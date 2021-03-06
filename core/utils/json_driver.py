import copy
import logging

from core.json_io import JsonIO
from pathlib import Path

__all__ = ["JSON"]

log = logging.getLogger("tbv.data_io")

_shared_datastore = {}

class JSON():
    def __init__(
            self,
            cog_name,
            data_path: Path = None,
            file_name: str = "settings.json"):
        self.cog_name = cog_name
        self.file_name = file_name
        if data_path:
            self.data_path = data_path
        else:
            self.data_path = Path.cwd() / "data" / "cogs" / self.cog_name

        self.data_path.mkdir(parents=True, exist_ok=True)
        self.data_path = self.data_path / self.file_name
        self.jsonIO = JsonIO(self.data_path)
        self._load_data()

    @property
    def data(self):
        return _shared_datastore.get(self.cog_name)

    @data.setter
    def data(self, value):
        _shared_datastore[self.cog_name] = value

    def _load_data(self):
        if self.data is not None:
            return
        
        try:
            self.data = self.jsonIO._load_json()
        except FileNotFoundError:
            self.data = {}
            self.jsonIO._save_json(self.data)

    async def get(self, *identifiers):
        partial = self.data
        for i in identifiers:
            partial = partial[i]
        return copy.deepcopy(partial)

    async def set(self, *identifiers, value):
        partial = self.data
        for i in identifiers[:-1]:
            if i not in partial:
                partial[i] = {}
            partial = partial[i]

        partial[identifiers[-1]] = copy.deepcopy(value)
        await self.jsonIO._threadsafe_save_json(self.data)

    async def clear(self, *identifiers):
        partial = self.data
        try:
            for i in identifiers[:-1]:
                partial = partial[i]
            del partial[identifiers[-1]]
        except KeyError:
            pass
        else:
            await self.jsonIO._threadsafe_save_json(self.data)
