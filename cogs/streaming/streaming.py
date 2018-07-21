# -*- coding: utf-8 -*-

import discord
from discord.ext import commands
from discord.webhook import Webhook, AsyncWebhookAdapter
from discord.channel import TextChannel

import asyncio
import aiohttp
import peony

import sys
import logging
import random
from typing import Tuple
import requests.packages.urllib3 as urllib3

from core.config import Config
from core import checks
from .embeds import prepare_embed

ReadTimeoutError = urllib3.exceptions.ReadTimeoutError

log = logging.getLogger("tbv.twitter")
default_webhook = {
    "url": "",
    "followed": [],
    "mention_role": ""
}

class Streaming:
    """The description for Twitter goes here."""

    def __init__(self, bot, config=Config):
        self.conf = config.get_cog_conf(self, force_registration=True)
        self.bot = bot
        self.client = None
        self._break_loop = False
        self._stream = None
        self._guilds = self.bot.guilds

        self.conf.register_global(
            auth__consumer_key = None,
            auth__consumer_secret = None,
            auth__access_token = None,
            auth__access_token_secret = None
        )

        self.conf.register_guild(
            phrases = [],
            channels = {}
        )

        # loop = asyncio.get_event_loop()
        # loop.create_task(self._init_client())
        # loop.create_task(self._start_stream())

    @commands.group()
    @checks.mod_or_permissions()
    @commands.guild_only()
    async def stream(self, ctx):
        """Allows to control twitter streaming manually."""
        pass

    @stream.command(name="start")
    @checks.is_owner()
    async def start(self, ctx, wh_name: str = "Name"):
        """Start streaming to the current channel."""
        await self._stop_stream()
        await self._init_client()

        ch_id = str(ctx.channel.id)
        channels = await self.conf.guild(ctx.guild).channels()

        if ch_id not in channels:
            channels[ch_id] = default_webhook

        if not channels[ch_id]["url"]:
            wh = await ctx.channel.create_webhook(name=wh_name)
            channels[ch_id]["url"] = wh.url
            await self.conf.guild(ctx.guild).channels.set(channels)

        self._stream = await self._start_stream()

    @stream.command(name="mention")
    @checks.mod_or_permissions()
    async def mention(self, ctx, role_name: str):
        """
        Adds role to mention when new tweet comes.

        Example:
        `[p]stream mention Listeners`
        """
        await self._stop_stream()
        await self._init_client()

        ch_id = str(ctx.channel.id)
        channels = await self.conf.guild(ctx.guild).channels()

        if ch_id not in channels:
            channels[ch_id] = default_webhook

        roles = ctx.guild.roles
        mention_role = None
        for role in roles:
            if role.name == role_name:
                mention_role = role
                break

        if not mention_role:
            await ctx.send(f"Could not find {role_name} role.")
            self._stream = await self._start_stream()
            return

        channels[ch_id]["mention_role"] = str(mention_role.id)
        await self.conf.guild(ctx.guild).channels.set(channels)
        self._stream = await self._start_stream()


    @stream.command(name="follow")
    @checks.mod_or_permissions()
    async def follow(self, ctx, id_):
        """
        Adds new account to the stream.

        Example:
        `[p]stream follow 123456`
        """
        await self._stop_stream()
        await self._init_client()

        ch_id = str(ctx.channel.id)
        channels = await self.conf.guild(ctx.guild).channels()

        if ch_id not in channels:
            channels[ch_id] = default_webhook

        if not channels[ch_id]["followed"]:
            channels[ch_id]["followed"] = [id_]
            await self.conf.guild(ctx.guild).channels.set(channels)
        if id_ not in channels[ch_id]["followed"]:
            channels[ch_id]["followed"].append(id_)
            await self.conf.guild(ctx.guild).channels.set(channels)
        else:
            await ctx.send("Already following ID")

        self._stream = await self._start_stream()

    @stream.command(name="unfollow")
    @checks.mod_or_permissions()
    async def unfollow(self, ctx, id_):
        """ 
        Removes an account from the stream.

        Examples:
        `[p]stream unfollow 123456`
        `[p]stream unfollow all`
        """
        await self._stop_stream()
        await self._init_client()

        ch_id = str(ctx.channel.id)
        channels = await self.conf.guild(ctx.guild).channels()

        if ch_id not in channels:
            channels[ch_id] = default_webhook

        if id_ == "all":
            channels[ch_id]["followed"] = []
            await self.conf.guild(ctx.guild).channels.set(channels)
        if id_ in channels[ch_id]["followed"]:
            channels[ch_id]["followed"].remove(id_)
            await self.conf.guild(ctx.guild).channels.set(channels)

        self._stream = await self._start_stream()

    @stream.command(name="stop")
    @checks.is_owner()
    async def stop(self, ctx):
        """Stops the stream."""
        await self._stop_stream()

    @commands.command(name="auth")
    @checks.is_owner()
    async def auth_twitter(
            self,
            ctx,
            key: str,
            secret: str,
            token: str,
            token_secret: str
    ):
        """Adds twitter authetication keys to the bot."""
        await self.conf.auth.consumer_key.set(key)
        await self.conf.auth.consumer_secret.set(secret)
        await self.conf.auth.access_token.set(token)
        await self.conf.auth.access_token_secret.set(token_secret)

    async def _start_stream(self):
        guilds = await self.conf.all_guilds()
        twitter_ids = []
        webhooks = []
        guilds_data = {}
        for guild in self._guilds:
            data = {
                "guild": guild,
                "webhooks": await guild.webhooks(),
                "channels": {
                    str(ch.id): ch for ch in guild.channels if (
                        isinstance(ch, TextChannel) and await ch.webhooks()
                    )
                }
            }
            guilds_data[guild.id] = data

        for guild, guild_data in guilds.items():
            for ch, ch_data in guild_data["channels"].items():
                twitter_ids.extend(ch_data.get("followed", []))
                if ch_data.get("url", ""):
                    data = {
                        "url": ch_data["url"],
                        "ids": ch_data["followed"],
                        "role": ch_data["mention_role"],
                        "channel": ch,
                        "guild": guild
                    }
                    webhooks.append(data)
        if not twitter_ids:
            return

        ctx = self.client.stream.statuses.filter.post(
            follow=twitter_ids
        )
        async with ctx as stream:
            self._stream = stream
            async for tweet in stream:
                if not peony.events.tweet(tweet):
                    continue
                if 'retweeted_status' in tweet:
                    continue
                if tweet["user"]["id_str"] not in twitter_ids:
                    continue
                embeds = prepare_embed(tweet)
                await self._send_webhooks(
                    tweet, embeds, webhooks, guilds_data
                )

    async def _init_client(self):
        auth = await self.conf.auth()
        self.client = peony.PeonyClient(**auth)

    async def _stop_stream(self):
        if self._stream:
            await self._stream.client.close()

    async def _send_webhooks(
            self,
            data,
            embeds,
            webhooks,
            guilds
    ):
        username = data["user"]["name"]
        icon_url = data["user"]["profile_image_url"]
        for webhook in webhooks:
            async with aiohttp.ClientSession() as session:
                if data["user"]["id_str"] not in webhook["ids"]:
                    continue
                wh = Webhook.from_url(
                    webhook["url"],
                    adapter=AsyncWebhookAdapter(session)
                )
                guild_id = webhook["guild"]
                ch_id = webhook["channel"]
                guild = guilds[guild_id]["guild"]
                channel = guilds[guild_id]["channels"][ch_id]
                mention_role = None
                phrases = await self.conf.guild(guild).phrases()
                content = ""
                if webhook["role"]:
                    permissions = channel.permissions_for(guild.me)
                    if not permissions.manage_roles:
                        continue
                    roles = guild.roles
                    for role in roles:
                        if str(role.id) == webhook["role"]:
                            mention_role = role
                            break
                    await mention_role.edit(mentionable=True)
                    await asyncio.sleep(2)
                    content = random.choice(phrases).format(mention_role.id)
                await wh.send(
                    content,
                    username=username,
                    avatar_url=icon_url,
                    embeds=embeds
                )
                if webhook["role"]:
                    await asyncio.sleep(2)
                    await mention_role.edit(mentionable=False)
