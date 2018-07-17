import logging
import appdirs
import os
import sys
from typing import List
from pathlib import Path
from .json_io import JsonIO

log = logging.getLogger("tbv.data_handler")

jsonio = None
basic_config = None

basic_config_default = {"DATA_PATH": None, "COG_PATH_APPEND": "cogs", "CORE_PATH_APPEND": "core"}

config_dir = None
appdir = appdirs.AppDirs("TheBotVanished")
if sys.platform == "linux":
    if 0 < os.getuid() < 1000:
        config_dir = Path(appdir.site_data_dir)
if not config_dir:
    config_dir = Path(appdir.user_config_dir)
config_file = config_dir / "config.json"


def load_basic_configuration():
    """Loads the basic bootstrap configuration necessary for `Config`
    to know where to store or look for data.

    .. important::
        It is necessary to call this function BEFORE getting any `Config`
        objects!
    """
    global jsonio
    global basic_config

    jsonio = JsonIO(config_file)

    try:
        basic_config = jsonio._load_json()
    except (FileNotFoundError, KeyError):
        print(
            "Missing basic config file"
        )
        sys.exit(1)


def _base_data_path() -> Path:
    if basic_config is None:
        raise RuntimeError("You must load the basic config before you can get the base data path.")
    path = basic_config["DATA_PATH"]
    return Path(path).resolve()


def cog_data_path(cog_instance=None) -> Path:
    """Gets the base cog data path. If you want to get the folder with
    which to store your own cog's data please pass in an instance
    of your cog class.

    Either ``cog_instance`` or ``raw_name`` will be used, not both.

    Parameters
    ----------
    cog_instance
        The instance of the cog you wish to get a data path for.
    raw_name : str
        The name of the cog to get a data path for.

    Returns
    -------
    pathlib.Path
        If ``cog_instance`` is provided it will return a path to a folder
        dedicated to a given cog. Otherwise it will return a path to the
        folder that contains data for all cogs.
    """
    try:
        base_data_path = Path(_base_data_path())
    except RuntimeError as e:
        raise RuntimeError(
            "You must load the basic config before you can get the cog data path."
        ) from e
    cog_path = base_data_path / basic_config["COG_PATH_APPEND"]

    if cog_instance is not None:
        cog_path = cog_path / cog_instance.__class__.__name__
    cog_path.mkdir(exist_ok=True, parents=True)

    return cog_path.resolve()


def core_data_path() -> Path:
    try:
        base_data_path = Path(_base_data_path())
    except RuntimeError as e:
        raise RuntimeError(
            "You must load the basic config before you can get the core data path."
        ) from e
    core_path = base_data_path / basic_config["CORE_PATH_APPEND"]
    core_path.mkdir(exist_ok=True, parents=True)

    return core_path.resolve()


def _find_data_files(init_location: str) -> (Path, List[Path]):
    """
    Discovers all files in the bundled data folder of an installed cog.

    Parameters
    ----------
    init_location

    Returns
    -------
    (pathlib.Path, list of pathlib.Path)
    """
    init_file = Path(init_location)
    if not init_file.is_file():
        return []

    package_folder = init_file.parent.resolve() / "data"
    if not package_folder.is_dir():
        return []

    all_files = list(package_folder.rglob("*"))

    return package_folder, [p.resolve() for p in all_files if p.is_file()]

