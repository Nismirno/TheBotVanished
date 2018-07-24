import asyncio

import peony
from discord.ext import commands
from discord.ext.commands import BucketType

from core.config import Config
from core import checks
from cogs.streaming.embeds import prepare_embed
from core.utils.chat_formatting import box

class Twitter:
    def __init__(self, bot, config=Config):
        self.client = None
        self.bot = bot
        self.conf = config.get_cog_conf(self, force_registration=True)
        self.tweets = {}
        self.conf.register_global(
            auth__consumer_key = None,
            auth__consumer_secret = None,
            auth__access_token = None,
            auth__access_token_secret = None
        )
        self.conf.register_guild(
            tweets = {},
            descriptions = {},
            accounts = {}
        )

        loop = asyncio.get_event_loop()
        loop.create_task(self._init_client())
        loop.create_task(self._load_tweets())

    @commands.group()
    @commands.guild_only()
    async def tweet(self, ctx):
        """
        Commands to post or update key tweets/followed accounts.
        """
        if ctx.invoked_subcommand is None:
            command = ctx.command
            destination = ctx
            embeds = await self.bot.formatter.format_help_for(ctx, command)
            for embed in embeds:
                try:
                    await destination.send(embed=embed)
                except discord.HTTPException:
                    destination = ctx.author
                    await destination.send(embed=embed)
        pass

    @tweet.command(name="post")
    @commands.guild_only()
    @commands.cooldown(1, 15, BucketType.user)
    async def post_tweet(self, ctx, *, content):
        """
        Post one of key tweets or one of the last tweets from followed accounts.

        Example:
        `[p]tweet post spaceship`
        `[p]tweet post tsv 13`
        """
        accounts = await self.conf.guild(ctx.guild).accounts()
        tweets = await self.conf.guild(ctx.guild).tweets()
        if any(keyword == content for keyword in tweets):
            await self._process_tweets(ctx, content)
            return
        if any(name in content for name in accounts):
            await self._process_accounts(ctx, content)
            return
        await ctx.send(
            f"Could not find account or keywords {content}.\n"
            "Please check keyword and account list."
        )
        ctx.command.reset_cooldown(ctx)

    @tweet.command(name="add")
    @commands.guild_only()
    @checks.mod_or_permissions()
    async def add_tweet(
            self,
            ctx,
            keyword: str,
            id_: str,
            *,
            description: str = ""
    ):
        """
        Adds new key tweet to the list.

        Description is optional.
        serverMod permission required.

        Example:
        `[p]tweet add spaceship 1001284425001431044 Image of spaceship`
        """
        tweets = await self.conf.guild(ctx.guild).tweets()
        desc = await self.conf.guild(ctx.guild).descriptions()
        if keyword in tweets:
            if id_ not in tweets[keyword]:
                tweets[keyword].append(id_)
        else:
            tweets[keyword] = [id_]

        if keyword not in desc:
            desc[keyword] = description
        await self.conf.guild(ctx.guild).tweets.set(tweets)
        await self.conf.guild(ctx.guild).descriptions.set(desc)
        await self._update_tweets(id_)

    @tweet.command(name="remove")
    @commands.guild_only()
    @checks.mod_or_permissions()
    async def remove_tweet(
            self,
            ctx,
            keyword: str,
            id_: str = ""
    ):
        """
        Remove key tweet or tweet from the list.
        
        serverMod permission required.

        Example:
        `[p]tweet remove spaceship 1001284425001431044 Image of spaceship`
        """
        tweets = await self.conf.guild(ctx.guild).tweets()
        desc = await self.conf.guild(ctx.guild).descriptions()
        if keyword not in tweets:
            await ctx.send("No such keyword in tweets list")
            tweets.pop(keyword, [])
            desc.pop(keyword, "")
        if not id_:
            statuses = tweets.pop(keyword, "")
            del desc[keyword]
            for status in statuses:
                self._update_tweets(status, True)
        else:
            if id_ in tweets[keyword]:
                tweets[keyword].remove(id_)
                self._update_tweets(id_, True)                
            else:
                await ctx.send("No ID associated with this keyword")
            if not tweets[keyword]:
                del tweets[keyword]
                del desc[keyword]
        await self.conf.guild(ctx.guild).tweets.set(tweets)
        await self.conf.guild(ctx.guild).descriptions.set(desc)

    @tweet.command(name="list")
    @commands.guild_only()
    @commands.cooldown(1, 30, BucketType.user)
    async def list_tweets(self, ctx):
        """Lists keyword with short descriptions."""
        descriptions = await self.conf.guild(ctx.guild).descriptions()
        key_str = "Keyword"
        desc_str = "Description"
        lang = f"{key_str:<20}{desc_str}"
        message = ""
        for key, desc in descriptions.items():
            message += f"{key:<20}{desc}\n"
        await ctx.send(box(message, lang=lang))

    @tweet.command(name="accounts")
    @commands.guild_only()
    @commands.cooldown(1, 30, BucketType.user)
    async def list_accounts(self, ctx):
        """Lists followed accounts."""
        accounts = await self.conf.guild(ctx.guild).accounts()
        lang = f"Following accounts:"
        message = ""
        for acc in accounts:
            message += f"{acc}\n"
        await ctx.send(box(message, lang=lang))


    @tweet.command(name="adduser")
    @commands.guild_only()
    @checks.mod_or_permissions()
    async def add_account(
            self,
            ctx,
            name: str,
            user: str,
    ):
        """
        Adds new account to follow list.

        serverMod permission required.

        Example:
        `[p]tweet adduser tsv 984234517308243968`
        `[p]tweet adduser nat LostSunNews`
        """
        accounts = await self.conf.guild(ctx.guild).accounts()
        is_id = False
        try:
            user = int(user)
            is_id = True
        except ValueError:
            pass
        if is_id:
            try:
                account = await self.client.api.users.show.get(
                    user_id=user
                )
            except peony.exceptions.NotFound as e:
                await ctx.send(e)
                return
            accounts[name] = account["id_str"]
        else:
            try:
                account = await self.client.api.users.show.get(
                    screen_name=user
                )
            except peony.exceptions.NotFound as e:
                await ctx.send(e)
                return
            accounts[name] = account["id_str"]
        await self.conf.guild(ctx.guild).accounts.set(accounts)

    @tweet.command(name="removeuser")
    @commands.guild_only()
    @checks.mod_or_permissions()
    async def remove_account(
            self,
            ctx,
            name: str
    ):
        """
        Remove account from follow list.

        serverMod permission required.

        Example:
        `[p]tweet removeuser nat`
        """
        accounts = await self.conf.guild(ctx.guild).accounts()
        if name not in accounts:
            await ctx.send(f"Could not find account {name}")
            return
        del accounts[name]
        await self.conf.guild(ctx.guild).accounts.set(accounts)

    async def _init_client(self):
        auth = await self.conf.auth()
        self.client = peony.PeonyClient(**auth)

    async def _load_tweets(self):
        guilds = await self.conf.all_guilds()
        for guild, guild_data in guilds.items():
            guild_tweets = guild_data["tweets"].values()
            for statuses in guild_tweets:
                for status in statuses:
                    try:
                        tweet = await self.client.api.statuses.show.get(
                            id=str(status), tweet_mode="extended"
                        )
                    except peony.exceptions.NotFound as e:
                        continue
                    self.tweets[str(status)] = tweet

    async def _update_tweets(
            self,
            status: str,
            to_remove: bool=False
    ):
        if not to_remove:
            tweet = await self.client.api.statuses.show.get(
                id=str(status), tweet_mode="extended"
            )
            self.tweets[str(status)] = tweet
        else:
            self.tweets.pop(status, "")

    async def _process_accounts(self, ctx, content):
        content = content.split()
        name = content[0]
        accounts = await self.conf.guild(ctx.guild).accounts()
        if name not in accounts:
            await ctx.send(f"Could not find account {name}")
            return
        id_ = accounts[name]
        try:
            statuses = await self.client.api.statuses.user_timeline.get(
                user_id=id_, tweet_mode="extended"
            )
        except Exception as e:
            await ctx.send(f"Unexcepted error {e}")
            return

        if len(content) > 1:
            try:
                i = int(content[1])
            except ValueError:
                await ctx.send("You must type a number after account name")
                return
            if i > 20:
                await ctx.send("You can access only last 20 tweets")
                return
            tweet = statuses[i-1]
        else:
            tweet = statuses[0]
        embeds = prepare_embed(tweet)
        for embed in embeds:
            await ctx.send(embed=embed)

    async def _process_tweets(self, ctx, content):
        keywords = await self.conf.guild(ctx.guild).tweets()
        if content not in keywords:
            await ctx.send(f"Could not find keywords {content}")
            return
        ids = keywords[content]
        for id_ in ids:
            tweet = self.tweets[id_]
            embeds = prepare_embed(tweet)
            for embed in embeds:
                await ctx.send(embed=embed)
