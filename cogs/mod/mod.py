# -*- coding: utf-8 -*-

from discord.ext import commands
from discord.channel import TextChannel
from discord.message import MessageType
import discord

from typing import Union
from datetime import datetime
from datetime import timedelta

from core.utils.mod import is_mod_or_superior
from core.config import Config
from core import checks

class Mod:
    """Moderator tools."""

    default_guild_settings = {
        "blacklist": [],
        "whitelist": [],
        "current_tempbans": [],
        "safe_roles": []
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

    @commands.command(name="lock")
    @checks.mod_or_permissions()
    async def lock_channel(self, ctx, channel: discord.TextChannel):
        """
        Auto deletes messages in channel

        Example:  
        `[p]lock #channel`
        """
        await self.conf.channel(channel).locked.set(True)

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
    async def _add(self, ctx, role_):
        """
        Add new role to the safe roles list.

        Example: 
        `[p]saferole set Member`
        """
        safe_roles = await self.conf.guild(ctx.guild).safe_roles()
        role = role_
        if isinstance(role, str):
            role = await self._resolve_role_name(ctx, role)
        if not isinstance(role, discord.Role):
            await ctx.send(f"Could not find role {str(role)}")
            return
        if role.id in safe_roles:
            return
        safe_roles.append(role.id)
        await self.conf.guild(ctx.guild).safe_roles.set(safe_roles)

    @saferole.command(name="remove")
    async def _remove(self, ctx, role_):
        """
        Remove role from safe roles list

        Example:
        `[p]saferole remove Member`
        """
        safe_roles = await self.conf.guild(ctx.guild).safe_roles()
        role = role_
        if isinstance(role, str):
            role = await self._resolve_role_name(ctx, role)
        if not isinstance(role, discord.Role):
            await ctx.send(f"Could not find role {str(role)}")
            return
        if role.id in safe_roles:
            return
        safe_roles.remove(role.id)
        await self.conf.guild(ctx.guild).safe_roles.set(safe_roles)

    @saferole.command(name="removeall")
    async def _removeall(self, ctx):
        """
        Remove all roles from safe roles list

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
        `[p]announce Listeners #announcments Tucker is alive!
        """
        guild = ctx.guild
        roles = guild.roles
        role_names = [role.name for role in roles]
        if mention not in role_names:
            await ctx.send(f"Could not find role {mention}")
            return
        role = None
        for r in roles:
            if mention==r.name:
                role = r
                break
        if not isinstance(channel, discord.TextChannel):
            channel = self._resolve_name(ctx, channel)
        await role.edit(mentionable=True)
        message = ' '.join([role.mention, message])
        await channel.send(content=message)
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
        Kicks user or all users with a selected role

        Examples: 
        `[p]kick @Username`
        `[p]kick Username`
        `[p]kick @Unverified`
        `[p]kick Unverified`
        """
        if isinstance(target, str):
            target = await self._resolve_name(ctx, target)
        if isinstance(target, discord.Role):
            await self._kick_role(ctx, target, reason)
            return
        if isinstance(target, discord.Member):
            await self._kick_user(ctx, target, reason)
            return
        await ctx.send("Could not find role or user {str(target)}")

    async def _kick_user(self, ctx, user: discord.Member, reason: str = ""):
        guild = ctx.guild
        members = guild.members
        if user in members:
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
        dm_message = f"You were kicked from {guild.name} server as you was not "
        dm_message += f"able to get access in 1 day time.\n"
        dm_message += "You can return to the server at any time to try again."
        for member in members_to_kick:
            dm_channel = await member.create_dm()
            try:
                await dm_channel.send(dm_message)
            except discord.errors.Forbidden:
                pass
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
