from discord.embeds import Embed
import random
import html
from datetime import datetime

def prepare_embed(data):
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
    text = None
    entities = None
    if "extended_tweet" in data:
        text = data["extended_tweet"]["full_text"]
        entities = data["extended_tweet"]["entities"]
    elif "full_text" in data:
        text = data["full_text"]
        entities = data.get("extended_entites", data["entities"])
    else:
        text = data["text"]
        entities = data["entities"]
    screenName = data["user"]["screen_name"]
    statusID = str(data["id_str"])
    url = f"https://twitter.com/{screenName}/status/{statusID}"
    ts = datetime.strptime(data["created_at"], '%a %b %d %H:%M:%S +0000 %Y')
    footerText = "Tweet created on"
    footerIcon = "https://cdn1.iconfinder.com/data/icons/iconza-circle-social/64/697029-twitter-512.png"
    hasVideo = False
    images = []

    if "media" in entities:
        for media in entities["media"]:
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
    if len(images):
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

