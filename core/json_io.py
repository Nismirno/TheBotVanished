import functools
import logging
import asyncio
import json
from pathlib import Path

log = logging.getLogger("tbv")

PRETTY = {"indent": 4, "sort_keys": True, "separators": (",", " : ")}
COMPACT = {"sort_keys": True, "separators": (",", ":")}

class JsonIO:
    def __init__(self, path: Path):
        self._lock = asyncio.Lock()
        if path:
            self.path = path
        else:
            raise ValueError("Please specifiy path to json file")

    def _save_json(self, data, settings=PRETTY):
        log.debug(f"Saving file {self.path}")
        with self.path.open(encoding="utf-8", mode="w") as f:
            json.dump(data, f, **settings)

    async def _threadsafe_save_json(self, data, settings=PRETTY):
        loop = asyncio.get_event_loop()
        func = functools.partial(self._save_json, data, settings)
        with await self._lock:
            await loop.run_in_executor(None, func)

    def _load_json(self):
        log.debug(f"Loading file {self.path}")
        with self.path.open(encoding="utf-8", mode="r") as f:
            data = json.load(f)
        return data

    async def _threadsafe_load_json(self):
        loop = asyncio.get_event_loop()
        with await self._lock:
            return await loop.run_in_executor(self._load_json)
