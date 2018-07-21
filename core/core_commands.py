from discord.ext import commands
from core import checks
import datetime
import discord
from .utils.chat_formatting import pagify, box, inline


class Core:
    """Core function commands."""
    def __init__(self, bot):
        self.bot = bot

    async def _prefixes(self, prefixes: list = None):
        """
        Gets or sets the bot's global prefixes.

        Parameters
        ----------
        prefixes : list of str
            If passed, the bot will set it's global prefixes.

        Returns
        -------
        list of str
            The current (or new) list of prefixes.
        """
        if prefixes:
            prefixes = sorted(prefixes, reverse=True)
            await self.bot.conf.prefix.set(prefixes)
        return await self.bot.conf.prefix()

    @commands.command()
    async def uptime(self, ctx):
        """Shows bot's uptime."""
        since = ctx.bot.uptime.strftime("%Y-%m-%d %H:%M:%S")
        passed = self.get_bot_uptime()
        await ctx.send("Been up for: **{}** (since {} UTC)".format(passed, since))

    def get_bot_uptime(self, *, brief=False):
        # Courtesy of Danny
        now = datetime.datetime.utcnow()
        delta = now - self.bot.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if not brief:
            if days:
                fmt = "{d} days, {h} hours, {m} minutes, and {s} seconds"
            else:
                fmt = "{h} hours, {m} minutes, and {s} seconds"
        else:
            fmt = "{h}h {m}m {s}s"
            if days:
                fmt = "{d}d " + fmt

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)

    @commands.group(name="set", autohelp=True)
    @checks.mod_or_permissions()
    async def _set(self, ctx):
        """Changes bot's settings."""
        if ctx.invoked_subcommand is None:
            if ctx.guild:
                admin_role_id = await ctx.bot.conf.guild(ctx.guild).admin_role()
                admin_role = discord.utils.get(ctx.guild.roles, id=admin_role_id) or "Not set"
                mod_role_id = await ctx.bot.conf.guild(ctx.guild).mod_role()
                mod_role = discord.utils.get(ctx.guild.roles, id=mod_role_id) or "Not set"
                prefixes = await ctx.bot.conf.guild(ctx.guild).prefix()
                guild_settings = f"Admin role: {admin_role}\nMod role: {mod_role}\n"
            else:
                guild_settings = ""
                prefixes = None  # This is correct. The below can happen in a guild.
            if not prefixes:
                prefixes = await ctx.bot.config.prefix()

            prefix_string = " ".join(prefixes)
            settings = (
                f"{ctx.bot.user.name} Settings:\n\n"
                f"Prefixes: {prefix_string}\n"
                f"{guild_settings}"
            )
            await ctx.send(box(settings))

    @_set.command()
    @checks.guildowner()
    @commands.guild_only()
    async def adminrole(self, ctx, *, role_):
        """Sets the admin role for this server."""
        role = role_
        if isinstance(role, str):
            role = await self._resolve_name(ctx, role)
        if not role:
            return
        await ctx.bot.config.guild(ctx.guild).admin_role.set(role.id)
        await ctx.send("The admin role for this guild has been set.")

    @_set.command()
    @checks.admin_or_permissions()
    @commands.guild_only()
    async def modrole(self, ctx, *, role_):
        """Sets the mod role for this server."""
        role = role_
        if isinstance(role, str):
            role = await self._resolve_name(ctx, role)
        if not role:
            return
        await ctx.bot.config.guild(ctx.guild).mod_role.set(role.id)
        await ctx.send("The mod role for this guild has been set.")

    @_set.command()
    @checks.is_owner()
    async def prefix(self, ctx, *prefixes):
        """Sets prefix globally."""
        if not prefixes:
            await ctx.send_help()
            return
        await self._prefixes(prefixes)
        await ctx.send("Prefix set.")

    @_set.command(aliases=["serverprefixes"])
    @checks.admin()
    @commands.guild_only()
    async def serverprefix(self, ctx, *prefixes):
        """Sets server prefix(es)."""
        if not prefixes:
            await ctx.bot.conf.guild(ctx.guild).prefix.set([])
            await ctx.send("Guild prefixes have been reset.")
            return
        prefixes = sorted(prefixes, reverse=True)
        await ctx.bot.conf.guild(ctx.guild).prefix.set(prefixes)
        await ctx.send("Prefix set.")

    @_set.command(name="game")
    @checks.bot_in_a_guild()
    @checks.is_owner()
    async def _game(self, ctx, *, game: str = None):
        """Sets bot's playing status."""
        activity_message = game
        if game:
            game = discord.Game(name=game)
        else:
            game = None
        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else discord.Status.online
        await ctx.bot.change_presence(status=status, game=game)
        await ctx.bot.conf.activity.set(activity_message)
        await ctx.send("Game set.")

    @commands.command(name="disablechannel")
    @checks.mod_or_permissions()
    @commands.guild_only()
    async def disable_channel(
            self,
            ctx,
            channel: discord.TextChannel
    ):
        """Disables commands in set channel."""
        if not isinstance(channel, discord.TextChannel):
            channel = await self._resolve_name(ctx, channel)
        channels = await ctx.bot.conf.guild(ctx.guild).disabled_channels()
        if channel.id not in channels:
            channels.append(channel.id)
        await ctx.bot.conf.guild(ctx.guild).disabled_channels.set(channels)
        await ctx.send(f"Commands in channel {channel} are disabled.")

    @commands.command(name="enablechannel")
    @checks.mod_or_permissions()
    @commands.guild_only()
    async def enable_channel(
            self,
            ctx,
            channel: discord.TextChannel
    ):
        """Enables commands in set channel."""
        if not isinstance(channel, discord.TextChannel):
            channel = await self._resolve_name(ctx, channel)
        channels = await ctx.bot.conf.guild(ctx.guild).disabled_channels()
        if channel.id in channels:
            channels.remove(channel.id)
        await ctx.bot.conf.guild(ctx.guild).disabled_channels.set(channels)
        await ctx.send(f"Commands in channel {channel} are enabled.")

    async def _resolve_name(self, ctx, name: str):
        guild = ctx.guild
        roles = guild.roles
        channels = guild.channels
        for role in roles:
            if role.name == name:
                return role
        for channel in channels:
            if channel.name == name:
                return channel
        await ctx.send(f"Could not find {name}")
        return None
