from core.data_manager import core_data_path, load_basic_configuration
from core.bot import TheBotVanished
from core.events import init_events
import os
import sys
import asyncio
import logging
import discord
import logging.handlers
import inspect
from pathlib import Path


def init_logging():
    # discord.py logs
    dpy_logger = logging.getLogger("discord")
    dpy_logger.setLevel(logging.INFO)

    tbv_logger = logging.getLogger("tbv")
    tbv_logger.setLevel(logging.WARNING)

    log_format = logging.Formatter(
        "%(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: %(message)s",
        datefmt="[%d/%m/%Y %H:%M]"
    )

    tbv_logfile = core_data_path() / "tbv.log"
    tbv_handler = logging.handlers.RotatingFileHandler(
        filename=str(tbv_logfile), encoding="utf-8", maxBytes = 10 * 2**20, backupCount=10
    )
    tbv_stdout_handler = logging.StreamHandler(sys.stdout)

    dpy_logfile = core_data_path() / "discord.log"
    dpy_handler = logging.FileHandler(
        filename=str(dpy_logfile), encoding="utf-8", mode="w"
    )

    tbv_handler.setFormatter(log_format)
    tbv_stdout_handler.setFormatter(log_format)
    dpy_handler.setFormatter(log_format)
    tbv_logger.addHandler(tbv_handler)
    tbv_logger.addHandler(tbv_stdout_handler)
    dpy_logger.addHandler(dpy_handler)
    
    return tbv_logger


async def get_token_and_prefix(bot, temp: dict):
    temp["token"] = await bot.config.token()
    temp["prefix"] = await bot.config.prefix()


def setup_token_and_prefix(bot, token_set: bool, prefix_set: bool):
    loop = asyncio.get_event_loop()
    token = ""
    prefix = ""

    if not token_set:
        print("Please enter valid token:")
        while not token:
            token = input("token: ")
            if not len(token) >= 50:
                print("That does not look like a valid token")
                token = ""
            if token:
                loop.run_until_complete(bot.config.token.set(token))

    if not prefix_set:
        print("Please enter desirable bot prefix:")
        while not prefix:
            prefix = input("prefix: ")
            if prefix:
                loop.run_until_complete(bot.config.prefix.set([prefix]))

    return token, prefix


def main():
    description = "TheBotVanished. Utility bot for TheSunVanished discord"
    load_basic_configuration()
    log = init_logging()
    tbv = TheBotVanished(description=description)
    init_events(tbv)
    loop = asyncio.get_event_loop()
    tmp_data = {}
    loop.run_until_complete(get_token_and_prefix(tbv, tmp_data))
    token = tmp_data["token"]
    prefix = tmp_data["prefix"]
    if not (token and prefix):
        token, prefix = setup_token_and_prefix(
            tbv, token_set=bool(token), prefix_set=bool(prefix)
        )
    try:
        loop.run_until_complete(tbv.start(token))
    except discord.LoginFailure:
        log.critical(
            "Bot login failed. Please enter correct token."
        )
    except KeyboardInterrupt:
        log.info("Keyboard interrupt detected. Shutting down...")
        loop.run_until_complete(tbv.logout())
    except Exception as e:
        log.critical("Fatal exception", exc_info=e)
        loop.run_until_complete(tbv.logout())
    finally:
        pending = asyncio.Task.all_tasks(loop=tbv.loop)
        gathered = asyncio.gather(*pending, loop=tbv.loop, return_exceptions=True)
        gathered.cancel()
        sys.exit(0)

if __name__ == "__main__":
    main()
