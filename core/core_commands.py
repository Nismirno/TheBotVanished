from discord.ext import commands
from core import checks
import datetime


class Core:
    """Core function commands."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def uptime(self, ctx):
        """Shows bot's uptime"""
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
        """Changes bot's settings"""
        if ctx.invoked_subcommand is None:
            if ctx.guild:
                admin_role_id = await ctx.bot.db.guild(ctx.guild).admin_role()
                admin_role = discord.utils.get(ctx.guild.roles, id=admin_role_id) or "Not set"
                mod_role_id = await ctx.bot.db.guild(ctx.guild).mod_role()
                mod_role = discord.utils.get(ctx.guild.roles, id=mod_role_id) or "Not set"
                prefixes = await ctx.bot.db.guild(ctx.guild).prefix()
                guild_settings = f"Admin role: {admin_role}\nMod role: {mod_role}\n"
            else:
                guild_settings = ""
                prefixes = None  # This is correct. The below can happen in a guild.
            if not prefixes:
                prefixes = await ctx.bot.db.prefix()

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
        """Sets the admin role for this server"""
        role = role_
        if isinstance(role, str):
            role = await self._resolve_role_name(ctx, role)
        if not role:
            return
        await ctx.bot.config.guild(ctx.guild).admin_role.set(role.id)
        await ctx.send(_("The admin role for this guild has been set."))

    @_set.command()
    @checks.admin_or_permissions()
    @commands.guild_only()
    async def modrole(self, ctx, *, role_):
        """Sets the mod role for this server"""
        role = role_
        if isinstance(role, str):
            role = await self._resolve_role_name(ctx, role)
        if not role:
            return
        await ctx.bot.config.guild(ctx.guild).mod_role.set(role.id)
        await ctx.send(_("The mod role for this guild has been set."))

    async def _resolve_role_name(self, ctx, name: str):
        guild = ctx.guild
        roles = guild.roles
        for role in roles:
            if role.name == name:
                return role
        await ctx.send(f"Could not find role {name}")
        return None
