import sys
import traceback
import codecs
import asyncio
import logging
import datetime

import discord
from discord.ext import commands

from . import __version__
from .utils.chat_formatting import bordered, inline, box
from .utils import fuzzy_command_search

logger = logging.getLogger("tbv")


def init_events(bot):
    @bot.event
    async def on_connect():
        if bot.uptime is None:
            print("Connected to Discord. Getting ready...")

    @bot.event
    async def on_ready():
        if bot.uptime is not None:
            return

        bot.uptime = datetime.datetime.utcnow()
        packages = await bot.conf.packages()
        activity_message = await bot.conf.activity()
        if activity_message:
            game = discord.Game(name=activity_message)
            status = discord.Status.online
            await bot.change_presence(status=status, game=game)

        if packages:
            to_remove = []
            print("Loading packages...")
            for package in packages:
                try:
                    bot.load_extension(package)
                except Exception as e:
                    logger.exception(f"Failed to load package {package}", exc_info=e)
                    to_remove.append(package)
            for package in to_remove:
                packages.remove(package)
            if packages:
                logger.info("Loaded packages: " + ", ".join(packages))

        guilds = len(bot.guilds)
        users = len(set([m for m in bot.get_all_members()]))

        try:
            data = await bot.application_info()
            invite_url = discord.utils.oauth_url(data.id)
        except:
            if bot.user.bot:
                invite_url = "Could not fetch invite url"
            else:
                invite_url = None

        prefixes = await bot.conf.prefix()
        bot_version = __version__
        dpy_version = discord.__version__

        INFO = [
            str(bot.user),
            f"Prefixes: {', '.join(prefixes)}",
            f"Bot version: {bot_version}",
            f"Discord.py version: {dpy_version}",
            f"Shards: {bot.shard_count}"
        ]

        if guilds:
            INFO.extend((f"Servers: {guilds}", f"Users: {users}"))
        else:
            print("Ready. I'm not im any server yet!")

        INFO.append(f"{len(bot.cogs)} cogs with {len(bot.commands)} commands.")

        on_symbol, off_symbol, ascii_border = _get_startup_screen_specs()

        print(bordered(INFO, ascii_border=ascii_border))

    @bot.event
    async def on_error(event_method, *args, **kwargs):
        logger.exception(f"Exception in {event_method}")

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await send_help(ctx)
        elif isinstance(error, commands.BadArgument):
            await send_help(ctx)
        elif isinstance(error, commands.DisabledCommand):
            await ctx.send("That command is disabled.")
        elif isinstance(error, commands.CommandInvokeError):
            """
            no_dms = "Cannot send messages to this user"
            is_help_cmd = ctx.command.qualified_name == "help"
            is_forbidden = isinstance(error.original, discord.Forbidden)
            if is_help_cmd and is_forbidden and error.original.text == no_dms:
                msg = ("I couldn't send the help message to you in DM. Either"
                       " you blocked me or you disabled DMs in this server.")
                await ctx.send(msg)
                return
            """
            logger.exception(
                "Exception in command '{}'" "".format(ctx.command.qualified_name),
                exc_info=error.original,
            )
            message = (
                "Error in command '{}'. Check your console or "
                "logs for details."
                "".format(ctx.command.qualified_name)
            )
            exception_log = "Exception in command '{}'\n" "".format(ctx.command.qualified_name)
            exception_log += "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            bot._last_exception = exception_log
            if not hasattr(ctx.cog, "_{0.command.cog_name}__error".format(ctx)):
                await ctx.send(inline(message))
        elif isinstance(error, commands.CommandNotFound):
            term = ctx.invoked_with + " "
            if len(ctx.args) > 1:
                term += " ".join(ctx.args[1:])
            fuzzy_result = await fuzzy_command_search(ctx, ctx.invoked_with)
            if fuzzy_result is not None:
                await ctx.maybe_send_embed(fuzzy_result)
        elif isinstance(error, commands.CheckFailure):
            pass
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("That command is not available in DMs.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                "This command is on cooldown. " "Try again in {:.2f}s" "".format(error.retry_after)
            )
        else:
            logger.exception(type(error).__name__, exc_info=error)

    @bot.event
    async def on_message(message):
        guild = message.guild
        channel = message.channel
        author = message.author
        is_mod = await bot.is_mod(author)
        is_owner = await bot.is_owner(author)
        disabled_channels = await bot.conf.guild(guild).disabled_channels()
        if channel.id in disabled_channels and not (is_mod or is_owner):
            return
        await bot.process_commands(message)


def _get_startup_screen_specs():
    """Get specs for displaying the startup screen on stdout.

    This is so we don't get encoding errors when trying to print unicode
    emojis to stdout (particularly with Windows Command Prompt).

    Returns
    -------
    `tuple`
        Tuple in the form (`str`, `str`, `bool`) containing (in order) the
        on symbol, off symbol and whether or not the border should be pure ascii.

    """
    encoder = codecs.getencoder(sys.stdout.encoding)
    check_mark = "\N{SQUARE ROOT}"
    try:
        encoder(check_mark)
    except UnicodeEncodeError:
        on_symbol = "[X]"
        off_symbol = "[ ]"
    else:
        on_symbol = check_mark
        off_symbol = "X"

    try:
        encoder("┌┐└┘─│")  # border symbols
    except UnicodeEncodeError:
        ascii_border = True
    else:
        ascii_border = False

    return on_symbol, off_symbol, ascii_border

async def send_help(ctx):
    """Send the command help message."""
    command = ctx.invoked_subcommand or ctx.command
    destination = ctx
    embeds = await ctx.bot.formatter.format_help_for(ctx, command)
    for embed in embeds:
        try:
            m = await destination.send(embed=embed)
        except discord.HTTPException:
            destination = ctx.author
            m = await destination.send(embed=embed)
            ret.append(m)
