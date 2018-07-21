__all__ = ["safe_delete", "fuzzy_command_search"]

import logging

from fuzzywuzzy import process
from discord.ext import commands

from .chat_formatting import box


def fuzzy_filter(record):
    return record.funcName != "extractWithoutOrder"


logging.getLogger().addFilter(fuzzy_filter)


async def filter_commands(ctx: commands.Context, extracted: list):
    return [
        i
        for i in extracted
        if i[1] >= 90
        and not i[0].hidden
        and await i[0].can_run(ctx)
        and all([await p.can_run(ctx) for p in i[0].parents])
        and not any([p.hidden for p in i[0].parents])
    ]


async def fuzzy_command_search(ctx: commands.Context, term: str):
    out = ""
    extracted_cmds = await filter_commands(
        ctx, process.extract(term, ctx.bot.walk_commands(), limit=5)
    )

    if not extracted_cmds:
        return None

    for pos, extracted in enumerate(extracted_cmds, 1):
        out += "{0}. {1.prefix}{2.qualified_name}{3}\n".format(
            pos,
            ctx,
            extracted[0],
            " - {}".format(extracted[0].short_doc) if extracted[0].short_doc else "",
        )
    return box(out, lang="Perhaps you wanted one of these?")
