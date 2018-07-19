#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import logging
from enum import Enum
from pathlib import Path
import datetime
import asyncio

import discord
from discord.ext.commands import Bot
from discord.ext.commands import when_mentioned_or

from .config import Config
from .help_formatter import Help, help as help_

log = logging.getLogger("tbv")

initial_extensions = (
    "cogs.mod"
)


class TheBotVanished(Bot):
    def __init__(self, *args, bot_dir: Path = Path.cwd(), **kwargs):
        self.config = Config.get_core_conf(force_registration=True)
        self.config.register_global(
            token=None,
            prefix=[],
            owner=None,
            embeds=True,
            color=15158332,
            help__page_char_limit=1000,
            help__max_pages_in_guild=2,
            help__tagline="",
        )
        self.config.register_guild(
            prefix=[],
            admin_role=None,
            mod_role=None,
            embeds=None,
            use_bot_color=False,
        )

        self.config.register_user(embeds=None)

        async def prefix_manager(bot, message):
            global_prefix = await bot.config.prefix()
            if message.guild is None:
                return global_prefix
            server_prefix = await bot.config.guild(message.guild).prefix()
            return (
                when_mentioned_or(*server_prefix)(bot, message)
                if server_prefix
                else when_mentioned_or(*global_prefix)(bot, message)
            )

        if "command_prefix" not in kwargs:
            kwargs["command_prefix"] = prefix_manager

        if "owner_id" not in kwargs:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._get_owner(kwargs))

        if "command_not_found" not in kwargs:
            kwargs["command_not_found"] = "Command {} not found.\n{}"

        self.main_dir = bot_dir

        super().__init__(formatter=Help(), **kwargs)

        self.remove_command("help")
        self.add_command(help_)

        for ext in initial_extensions:
            try:
                self.load_extension(ext)
            except Exception as e:
                print(f"Failed to load extension {ext}", file=sys.stderr)
                log.exception(f"Failed to load extension {ext}")

    async def _get_owner(self, indict):
        indict["owner_id"] = await self.config.owner()

    async def is_admin(self, member: discord.Member):
        admin_role = await self.config.guild(member.guild).admin_role()
        return any(role.id == admin_role for role in memeber.roles)

    async def is_mod(self, member: discord.Member):
        mod_role = await self.config.guild(member.guild).mod_role()
        admin_role = await self.config.guild(member.guild).admin_role()
        return any(role.id in (admin_role, mod_role) for role in memeber.roles)

    async def embed_requested(self, channel, user, command=None) -> bool:
        """
        Determine if an embed is requested for a response.

        Parameters
        ----------
        channel : `discord.abc.GuildChannel` or `discord.abc.PrivateChannel`
            The channel to check embed settings for.
        user : `discord.abc.User`
            The user to check embed settings for.
        command
            (Optional) the command ran.

        Returns
        -------
        bool
            :code:`True` if an embed is requested
        """
        if isinstance(channel, discord.abc.PrivateChannel) or (
            command and command == self.get_command("help")
        ):
            user_setting = await self.config.user(user).embeds()
            if user_setting is not None:
                return user_setting
        else:
            guild_setting = await self.config.guild(channel.guild).embeds()
            if guild_setting is not None:
                return guild_setting
        global_setting = await self.config.embeds()
        return global_setting

    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            self.uptime = datetime.datetime.utcnow()
        print(f"Ready {self.user} (ID: {self.user.id})")
        self.load_extension("cogs.streaming")
