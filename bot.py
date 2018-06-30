import discord
from discord.message import MessageType
from discord.ext import commands
from twitterHandle import TwitterHandle
from discord.embeds import Embed
from datetime import datetime
from datetime import timedelta
from typing import Union, Optional
import json
import random
import html
import logging


logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)

handler = logging.FileHandler(filename="discord.log",
                              encoding="utf-8",
                              mode='w')
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s:%(levelname)s:%(name)s %(message)s"))
logger.addHandler(handler)
with open("data.json") as d:
    data = json.load(d)

TOKEN = data["Discord"]["token"]
CONSUMER_KEY = data["Twitter"]["consumer-key"]
CONSUMER_SECRET = data["Twitter"]["consumer-secret"]
ACCESS_TOKEN = data["Twitter"]["access-token"]
ACCESS_TOKEN_SECRET = data["Twitter"]["access-token-secret"]
MAXTWEETS = 20

description = """Simple bot for handling tweets
from TSV (@TheSunVanished) and Tucker (@thmadjoy)"""

bot = commands.Bot(command_prefix='-', description=description)
twitter = TwitterHandle()
userIDs = {"tsv": "984234517308243968",
           "tucker": "994077432897523713"}
importantTweets = {"first encounter": ["991537892974628864"],
                   "stars": ["991540490712514560"],
                   "heat": ["991704363080015872",
                            "992095357617127424",
                            "992097650043334656",
                            "993219119800573952"],
                   "danyon intro": ["992186003824762880",
                                    "992186272788738048",
                                    "992187930398613505"],
                   "tranced person": ["992192628287516672",
                                      "992193987921567744",
                                      "992194748483063808",
                                      "992220920096976896",
                                      "992230769174118406",
                                      "992244435026169856"],
                   "bc": ["992619707432828928",
                          "995860972458962944"],
                   "screaming": ["992989445182935041"],
                   "red light": ["993709748267683840",
                                 "993714245484318725"],
                   "tucker intro": ["994091501985632258"],
                   "intrusion": ["994424394754732033",
                                 "994434436547665921"],
                   "headlights info": ["994729995716177920"],
                   "neighbor house": ["997322492929769473"],
                   "water": ["999734193801265152"],
                   "note": ["1000486534146154498"],
                   "spaceship": ["1001284425001431044"],
                   "blue light": ["998672244854480896",
                                  "1001579421109800960"],
                   "journal": ["1002762807035736065",
                               "1002763771012698112",
                               "1002765355180285952",
                               "1002771616907087872"],
                   "body": ["1002289486544490499",
                            "1002293338140274688",
                            "1004241447351177216"],
                   "virginia": ["994441330100260864"],
                   "global": ["994651789210390528"],
                   "west coast": ["996429172405829632"]
                   }


def makeEmbedTweet(data):
    colors = ['7f0000', '535900', '40d9ff', '8c7399', 'd97b6c',
              'f2ff40', '8fb6bf', '502d59', '66504d', '89b359',
              '00aaff', 'd600e6', '401100', '44ff00', '1a2b33',
              'ff00aa', 'ff8c40', '17330d', '0066bf', '33001b',
              'b39886', 'bfffd0', '163a59', '8c235b', '8c5e00',
              '00733d', '000c59', 'ffbfd9', '4c3300', '36d98d',
              '3d3df2', '590018', 'f2c200', '264d40', 'c8bfff',
              'f23d6d', 'd9c36c', '2db3aa', 'b380ff', 'ff0022',
              '333226', '005c73', '7c29a6']
    color = random.choice(colors)
    color = int(color, 16)

    title = data["user"]["name"]
    if "full_text" in data:
        text = data["full_text"]
    else:
        text = data["text"]
    screenName = data["user"]["screen_name"]
    statusID = str(data["id_str"])
    url = f"https://twitter.com/{screenName}/status/{statusID}"
    ts = datetime.strptime(data["created_at"], '%a %b %d %H:%M:%S +0000 %Y')
    footerText = "Tweet created on"
    footerIcon = "https://cdn1.iconfinder.com/data/icons/iconza-circle-social/64/697029-twitter-512.png"
    hasVideo = False
    images = []
    extendedTweet = False
    if ("extended_entities" in data and "media" in data["extended_entities"]):
        extendedTweet = True
        for media in data["extended_entities"]["media"]:
            if media["type"] != "video":
                mediaFile = media["media_url_https"]
                images.append(mediaFile)
            else:
                hasVideo = True

    if not extendedTweet:
        if ("entities" in data and "media" in data["entities"]):
            for media in data["entities"]["media"]:
                if media["type"] != "video":
                    mediaFile = media["media_url_https"]
                    images.append(mediaFile)
                else:
                    hasVideo = True

    if hasVideo:
        text += " _tweet has a video_"
    author = {"name": title,
              "url": f"https://twitter.com/{screenName}",
              "icon_url": data['user']['profile_image_url']}
    text = html.unescape(text)

    embedData = {"title": title,
                 "type": "rich",
                 "description": text,
                 "url": url,
                 "color": color,
                 "author": author}

    embeds = [Embed.from_data(embedData)]
    embeds[0].set_footer(text=footerText, icon_url=footerIcon)
    embeds[0].timestamp = ts
    embeds[0].timestamp = ts
    if len(images) and not hasVideo:
        embeds[0].set_image(url=images[0])
    if len(images) < 2:
        return embeds
    for i in range(1, len(images)):
        embedData = {"title": title,
                     "author": author,
                     "url": url,
                     "color": color,
                     "type": "rich"}
        embeds.append(Embed.from_data(embedData))
        embeds[-1].set_image(url=images[i])
        embeds[-1].set_footer(text=footerText, icon_url=footerIcon)
        embeds[-1].timestamp = ts
        return embeds


def not_welcome_channel():
    def predicate(ctx):
        return ctx.message.channel.id != 446432988104884224
    return commands.check(predicate)


def is_owner(ctx):
    author = ctx.message.author
    owner = ctx.guild.owner
    return (owner is not None and author.id == owner.id)


def has_permissions(**perms):
    def predicate(ctx):
        if is_owner(ctx):
            return True
        if not perms:
            return False

        ch = ctx.message.channel
        author = ctx.message.author
        resolved = ch.permissions_for(author)
        return all(getattr(resolved, name, None) == value
                   for name, value in perms.items())
    return commands.check(predicate)


@bot.event
async def on_ready():
    print("Logged in as")
    print(bot.user.name)
    print(bot.user.id)
    for guild in bot.guilds:
        print(guild.name, guild.id)
    print("------")


@bot.event
async def on_message(message: discord.Message):
    author = message.author
    type_ = message.type
    is_bot = author.bot
    author_roles_id = [role.id for role in author.roles]
    is_mod = 446430809000247297 in author_roles_id
    is_admin = author.guild_permissions.administrator
    is_owner = (author.guild.owner == author)
    is_welcome = type == MessageType.new_member
    if not (is_bot or is_mod or is_admin or is_owner or is_welcome):
        if message.channel.id == 446432988104884224:
            await message.delete()
    await bot.process_commands(message)


@bot.command()
@not_welcome_channel()
@commands.cooldown(1, 10, commands.BucketType.user)
async def tweet(ctx: commands.Context, *args):
    """
    Command to post one of the tweets from TSV or Tucker

    Usage:
    -tweet username: posts last tweet from chosen account
    Example -tweet tucker

    -tweet username n: posts nth tweet out of last 20
    Example -tweet tsv 15

    -tweet "keyword": posts tweets which correspond to a chosen keyword
    Example -tweet "first encounter"
    """
    try:
        if not args:
            text = "Specify username. Available usernames: \n"
            for key in userIDs:
                text += f"`{key}`\n"
            await ctx.send(text)
            return
        if (args[0] in userIDs):
            if len(args) == 2:
                if int(args[1]) > MAXTWEETS:
                    await ctx.send(f"Number should be between 1 and {MAXTWEETS}")
                    return
                tweet = twitter.getTweet(userID=userIDs[args[0]],
                                         iTweet=int(args[1])-1)
                embeds = makeEmbedTweet(tweet)
                for embed in embeds:
                    await ctx.send(embed=embed)
                return
            else:
                tweet = twitter.getTweet(userID=userIDs[args[0]],
                                         iTweet=0)
                embeds = makeEmbedTweet(tweet)
                for embed in embeds:
                    await ctx.send(embed=embed)
                return
        if args[0] in importantTweets:
            statusIDs = importantTweets[args[0]]
            for status in statusIDs:
                tweet = twitter.getTweet(statusID=status)
                embeds = makeEmbedTweet(tweet)
                for embed in embeds:
                    await ctx.send(embed=embed)
            return
        else:
            text = "Unknown keyword or account name\n"
            text += "Please use `-list` command for a keyword list or `-accounts` for a list of available account names"
            await ctx.send(text)
            return
        text = "Unknown format\n"
        text += "Please consult with `-help tweet` to see examples of command format"
        await ctx.send(text)
        return
    except commands.errors.CommandOnCooldown as e:
        await ctx.send(e)


@bot.command()
@not_welcome_channel()
async def list(ctx):
    """
    Posts a list of keyword which can be used with -tweet command
    """
    text = "Here is a list of available keywords\n"
    text += "```\n"
    for key in importantTweets:
        text += key + "\n"
    text += "```"
    await ctx.send(text)


@bot.command()
@not_welcome_channel()
async def accounts(ctx):
    """
    Posts a list of accounts which can be used with -tweet command
    """
    text = "Here is a list of available account names\n"
    text += "```\n"
    for key in userIDs:
        text += key + "\n"
    text += "```"
    await ctx.send(text)


@bot.command()
@has_permissions(kick_members=True)
async def kickrole(ctx, roleName: str = None,
                   delta: str = None):
    """
    Allows for moderator to kick users which have a specific role
    """
    await ctx.message.delete()
    timeUnits = {'w': 7,
                 'd': 1,
                 'h': None}
    if (not roleName):
        await ctx.send("Please specify role")
        return
    if delta:
        if delta.isalpha():
            await ctx.send("Missing number of weeks/days/hours")
            return
        elif delta.isdigit():
            time = int(delta)
            requiredDelta = timedelta(days=time)
        elif (delta[:-1].isdigit() and delta[-1].isalpha()):
            unit = delta[-1]
            if (unit not in timeUnits):
                await ctx.send("Unspecified time unit. Please use w, d or h")
                return
            elif unit == 'h':
                time = int(delta[:-1])
                requiredDelta = timedelta(hours=time)                
            else:
                time = int(delta[:-1]) * timeUnits[unit]
                requiredDelta = timedelta(days=time)
    else:
        requiredDelta = timedelta(days=1)
    currentTime = datetime.utcnow()
    guild = ctx.guild
    roleNames = [role.name.lower() for role in guild.roles]
    if roleName.lower() not in roleNames:
        text = f"Could not find {roleName} role on the server"
        await ctx.send(text)
        return
    users = guild.members
    selectedUsers = []
    for user in users:
        userRoleNames = [role.name.lower() for role in user.roles]
        if roleName.lower() not in userRoleNames:
            continue
        userTime = currentTime - user.joined_at
        if userTime > requiredDelta:
            selectedUsers.append(user)
    reason = "Daily cleaning of welcome channel"
    if requiredDelta.days > 1:
        mTime = f"{str(requiredDelta.days)} days"
    elif requiredDelta.days == 1:
        mTime = f"{str(requiredDelta.days)} day"
    elif requiredDelta.seconds > 3600:
        mTime = f"{str(requiredDelta.seconds // 3600)} hours"
    else:
        mTime = f"{str(requiredDelta.seconds // 3600)} hour"
    userMessage = f"You were kicked from {guild.name} server as you was not "
    userMessage += f"able to get access in {mTime} time.\n"
    userMessage += "You can return to the server at any time to try again."
    for user in selectedUsers:
        dmChannel = await user.create_dm()
        try:
            await dmChannel.send(userMessage)
        except discord.errors.Forbidden:
            pass
        await user.kick(reason=reason)
    return


bot.run(TOKEN)
