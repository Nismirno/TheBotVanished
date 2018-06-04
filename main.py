import discord
from discord.ext import commands
from twitterHandle import TwitterHandle
from discord.embeds import Embed
from datetime import datetime
from pprint import pprint
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
importantTweets = {}


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
    imageURL = ""
    hasVideo = False
    if ("entities" in data and "media" in data["entities"]):
        media = data["entities"]["media"]
        if (len(media) == 1):
            if media[0]["type"] != "video":
                imageURL = media[0]["media_url_https"]
            else:
                hasVideo = True

    if ("extended_entities" in data and "media" in data["extended_entities"]):
        media = data["extended_entities"]["media"]
        if (len(media) == 1):
            if media[0]["type"] != "video":
                imageURL = media[0]["media_url_https"]
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
                 "colour": color,
                 "author": author}

    newEmbed = Embed.from_data(embedData)
    newEmbed.set_footer(text=footerText, icon_url=footerIcon)
    newEmbed.timestamp = ts
    if imageURL and not hasVideo:
        newEmbed.set_image(url=imageURL)
    return newEmbed


@bot.event
async def on_ready():
    print("Logged in as")
    print(bot.user.name)
    print(bot.user.id)
    for server in bot.servers:
        print(dir(server))
    print("------")


@bot.command()
async def tweet(*args):
    """
    Command to post one of the tweets from TSV or Tucker

    Parameters
    ----------
    i : Optional[int]
        Picks a i-th tweet from the last N tweets from chosen account
    name : Optional[str]
        Choses between TSV or Tucker accounts (default: TSV)
    """
    if not args:
        tweet = twitter.getTweet(userID=userIDs["tsv"],
                                 iTweet=0)
        if tweet:
            embed = makeEmbedTweet(tweet)
            await bot.say(embed=embed)
            return
        else:
            await bot.say("<@177856625485414400> Something went wrong")
    if (args[0] in userIDs) and (args[1].isdigit()):
        if int(args[1]) > MAXTWEETS:
            await bot.say(f"Number should be between 1 and {MAXTWEETS}")
            return
        tweet = twitter.getTweet(userID=userIDs[args[0]],
                                 iTweet=int(args[1])-1)
        embed = makeEmbedTweet(tweet)
        await bot.say(embed=embed)
        return
    if args[0].isdigit():
        tweet = twitter.getTweet(userID=userIDs["tsv"],
                                 iTweet=int(args[0])-1)
        embed = makeEmbedTweet(tweet)
        await bot.say(embed=embed)
        return
    if args[0] in importantTweets:
        statusID = importantTweets[args[0]]
        tweet = twitter.getTweet(statusID=statusID)
        embed = makeEmbedTweet(tweet)
        await bot.say(embed=embed)
        return

bot.run(TOKEN)
