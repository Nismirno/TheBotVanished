import appdirs
import sys
import os
from pathlib import Path
from core.json_io import JsonIO

basic_config_default = {"DATA_PATH": None, "COG_PATH_APPEND": "cogs", "CORE_PATH_APPEND": "core"}

config_dir = None
appdir = appdirs.AppDirs("TheBotVanished")
if sys.platform == "linux":
    if 0 < os.getuid() < 1000:
        config_dir = Path(appdir.site_data_dir)
if not config_dir:
    config_dir = Path(appdir.user_config_dir)
try:
    config_dir.mkdir(parents=True, exist_ok=True)
except PermissionError:
    print("You don't have permission to write to '{}'\nExiting...".format(config_dir))
    sys.exit(1)
config_file = config_dir / "config.json"


def confirm(m=""):
    return input(m).lower().strip() in ("y", "yes")


def load_config():
    if not config_file.exists():
        return {}
    return JsonIO(config_file)._load_json()


def save_config(data):
    config = load_config()
    if not config:
        print(
            "WARNING: This will overwrite existing config."
        )
        if not confirm("Do you want to continue? (y/n) "):
            print("Not continuing")
            sys.exit(0)
    config = data
    JsonIO(config_file)._save_json(config)


def basic_setup():
    """ 
    Function to set up basic configuration of the bot automatically
    This creates data storage folder
    """
    default_data_dir = Path(appdir.user_data_dir)
    default_dirs = {}
    default_dirs["DATA_PATH"] = str(default_data_dir.resolve())
    default_dirs["COG_PATH_APPEND"] = "cogs"
    default_dirs["CORE_PATH_APPEND"] = "core"
    default_dirs["STORAGE_DETAILS"] = {}
    save_config(default_dirs)
    print("Created default data dir in "
          f"{str(default_data_dir)}")
    pass


if __name__ == "__main__":
    basic_setup()
