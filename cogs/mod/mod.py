# -*- coding: utf-8 -*-
import logging
from typing import Union
from datetime import datetime
from datetime import timedelta

import discord
from discord.ext import commands
from discord.message import MessageType

from core.utils.mod import is_mod_or_superior
from core.config import Config
from core import checks

logger = logging.getLogger("tbv.mod")


class Mod:
    """Moderator tools."""

    default_guild_settings = {
        "blacklist": [],
        "whitelist": [],
        "current_tempbans": [],
        "safe_roles": [],
        "voice_text_role": None
    }

    default_channel_settings = {"locked": False}

    default_member_settings = {"past_nicks": [], "banned_until": False}

    default_user_settings = {"past_names": []}

    def __init__(self, bot, config=Config):
        self.bot = bot
        self.conf = config.get_cog_conf(self, force_registration=True)
        self.conf.register_guild(**self.default_guild_settings)
        self.conf.register_channel(**self.default_channel_settings)
        self.conf.register_member(**self.default_member_settings)
        self.conf.register_user(**self.default_user_settings)

    async def on_message(self, message: discord.Message):
        author = message.author
        if message.guild is None or self.bot.user == author:
            return
        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            return
        mod_or_superior = await is_mod_or_superior(self.bot, obj=author)
        if mod_or_superior:
            return
        locked = await self.conf.channel(message.channel).locked()
        if message.type == MessageType.new_member:
            return
        if locked:
            await message.delete()

    async def on_voice_state_update(
            self,
            member: discord.Member,
            before: discord.VoiceState,
            after: discord.VoiceState
    ):
        guild = member.guild
        channel_before = before.channel
        channel_after = after.channel
        if channel_before and channel_after:
            return
        role_id = await self.conf.guild(guild).voice_text_role()
        voice_text_role = discord.utils.get(
            guild.roles,
            id=int(role_id)
        )
        if not voice_text_role:
            logger.warning(f"Could not find role {role_id}")
            return
        if not channel_before and channel_after:
            await member.add_roles(voice_text_role)
            return
        if not channel_after and channel_before:
            await member.remove_roles(voice_text_role)

    @commands.group()
    @commands.guild_only()
    async def voice(self, ctx):
        """
        Helper commands for voice channels.
        """
        pass

    @voice.command(name="setrole")
    @checks.mod_or_permissions()
    async def _set_voice_role(self, ctx, role: discord.Role):
        """
        Sets a role to use text channel associated with voice channel.

        Example:
        `[p]voice setrole Speakers`
        """
        role_ = role
        if isinstance(role, str):
            role_ = discord.utils.get(ctx.guild.roles, name=role)
        if not role_:
            await ctx.send(f"Could not find role {role}")
            return
        await self.conf.guild(ctx.guild).voice_text_role.set(role_.id)
        await ctx.send(f"Set role {role_} for voice channel")

    @commands.command(name="lock")
    @checks.mod_or_permissions()
    async def lock_channel(self, ctx, channel: discord.TextChannel):
        """
        Locks channel for everyone except mods and bots.

        Locking means auto-deletion of messages.

        Example:
        `[p]lock #channel`
        """
        channel_ = channel
        if isinstance(channel, str):
            channel_ = discord.utils.get(ctx.guild.channels, name=channel)
        if not channel_:
            await ctx.send(f"Could not find channel {channel}")
        await self.conf.channel(channel_).locked.set(True)
        await ctx.send(f"Locked channel {channel_} for posting")

    @commands.command(name="unlock")
    @checks.mod_or_permissions()
    async def unlock_channel(self, ctx, channel: discord.TextChannel):
        """
        Unlocks channel for users.

        Example:
        `[p]unlock #channel`
        """
        channel_ = channel
        if isinstance(channel, str):
            channel_ = discord.utils.get(ctx.guild.channels, name=channel)
        if not channel_:
            await ctx.send(f"Could not find channel {channel}")
        await self.conf.channel(channel_).locked.set(False)
        await ctx.send(f"Unlocked channel {channel_} for posting")

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions()
    async def saferole(self, ctx):
        """
        Role list of safe roles.

        Used to prevent accidentially kicking all users.
        """
        pass

    @saferole.command(name="add")
    async def _add(self, ctx, role: discord.Role):
        """
        Add new role to the safe roles list.

        Example:
        `[p]saferole set Member`
        """
        role_ = role
        safe_roles = await self.conf.guild(ctx.guild).safe_roles()
        if isinstance(role, str):
            role_ = discord.utils.get(ctx.guild.roles, name=role)
        if not role_:
            await ctx.send(f"Could not find role {role}")
            return
        if role_.id in safe_roles:
            await ctx.send("Role is already in the list")
            return
        safe_roles.append(role_.id)
        await self.conf.guild(ctx.guild).safe_roles.set(safe_roles)
        await ctx.send(f"Added role {role_} to safe roles")

    @saferole.command(name="remove")
    async def _remove(self, ctx, role: discord.Role):
        """
        Remove role from safe roles list

        Example:
        `[p]saferole remove Member`
        """
        safe_roles = await self.conf.guild(ctx.guild).safe_roles()
        role_ = role
        if isinstance(role, str):
            role_ = discord.utils.get(ctx.guild.roles, name=role)
        if not role_:
            await ctx.send(f"Could not find role {role}")
            return
        if role_.id not in safe_roles:
            await ctx.send("Role not in the list")
            return
        safe_roles.remove(role_.id)
        await self.conf.guild(ctx.guild).safe_roles.set(safe_roles)
        await ctx.send(f"Removed role {role_} from safe roles")

    @saferole.command(name="removeall")
    async def _removeall(self, ctx):
        """
        Remove all roles from safe roles list.

        Example:
        `[p]saferole removeall`
        """
        await self.conf.guild(ctx.guild).safe_roles.set([])

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_roles=True)
    async def announce(
            self,
            ctx,
            mention: str,
            channel: discord.TextChannel,
            *,
            message: str
    ):
        """
        Do a server wide announce for a set role.

        Example:
        `[p]announce Listeners #announcments Tucker is alive!`
        """
        role = discord.utils.get(ctx.guild.roles, name=mention)
        if not role:
            await ctx.send(f"Could not find role {mention}")
            return
        channel_ = channel
        if not isinstance(channel, discord.TextChannel):
            channel_ = discord.utils.get(ctx.guild.channels, name=channel)
        if not channel_:
            await ctx.send(f"Could not find channel {channel}")
            return
        disable = True
        if role.mentionable:
            disable = False
        await role.edit(mentionable=True)
        message = ' '.join([role.mention, message])
        await channel.send(content=message)
        if disable:
            await role.edit(mentionable=False)

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(kick_members=True)
    async def kick(
            self,
            ctx,
            target,
            *,
            reason: str = ""
    ):
        """
        Kicks user or all users with a selected role.

        Examples:
        `[p]kick @Username`
        `[p]kick Username`
        `[p]kick @Unverified`
        `[p]kick Unverified`
        """
        members = [target]
        role = target
        if isinstance(target, str):
            members = [member for member in ctx.guild.members
                       if member.name == target]
            role = discord.utils.get(ctx.guild.roles, name=target)
        if isinstance(role, discord.Role):
            await self._kick_role(ctx, role, reason)
            return
        if len(members) > 1:
            await ctx.send("More than one user have that name."
                           "Use mention instead")
            return
        if members:
            await self._kick_user(ctx, members[0], reason)
            return
        await ctx.send("Could not find role or user {target}")

    async def _kick_user(self, ctx, user: discord.Member, reason: str = ""):
        guild = ctx.guild
        members = guild.members
        if user in members:
            dm_channel = await user.create_dm()
            if not reason:
                reason = "unspecified"
            dm_message = f"You were kicked from {guild.name} with reason: "
            dm_message += f"{reason}.\n"
            try:
                await dm_channel.send(dm_message)
            except discord.errors.Forbidden:
                logger.info(f"Could not send a DM to {user.name}")
            await user.kick(reason=reason)

    async def _kick_role(self, ctx, role: discord.Role, reason_: str = ""):
        await ctx.message.delete()
        guild = ctx.guild
        roles = guild.roles
        safe_roles = await self.conf.guild(guild).safe_roles()
        if role not in roles:
            await ctx.send(f"Could not find role {str(role)}")
            return
        time_delta = timedelta(days=1)
        current_time = datetime.utcnow()
        members = guild.members
        members_to_kick = []
        for member in members:
            mod_or_superior = await is_mod_or_superior(self.bot, obj=member)
            if mod_or_superior:
                continue
            member_role_ids = set([role.id for role in member.roles])
            if (set(safe_roles) & member_role_ids):
                continue
            if role not in member.roles:
                continue
            time_since_joined = current_time - member.joined_at
            if time_since_joined > time_delta:
                members_to_kick.append(member)
        reason = "Daily cleaning of welcome channel"
        if reason_:
            reason = reason_
        dm_message = f"You were kicked from {guild.name} server "
        dm_message += "as you was not able to get access in 1 day time."
        dm_message += "You can return to the server at any time to try again.\n"
        invites = [i for i in await guild.invites() if i.max_age == 0]
        invite = max(invites, key=lambda x: x.uses)
        dm_message += f"{invite.url}"
        for member in members_to_kick:
            dm_channel = await member.create_dm()
            try:
                await dm_channel.send(dm_message)
            except discord.errors.Forbidden:
                logger.info(f"Could not send a DM to {member.name}")
            await member.kick(reason=reason)

    async def _resolve_name(
            self, ctx, name: str
    ) -> Union[discord.Member, discord.Role, discord.TextChannel]:
        guild = ctx.guild
        roles = guild.roles
        channels = guild.channels
        for role in roles:
            if role.name == name:
                return role
        members = guild.members
        selected_members = []
        for member in members:
            if member.nick == name or member.name == name:
                selected_members.append(member)
        if len(selected_members) == 1:
            return selected_members[0]
        for channel in channels:
            if channel.name == name:
                return channel
        return None
