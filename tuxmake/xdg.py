import os
from pathlib import Path


def _resolve(var, default):
    home = os.getenv(var)
    if home:
        return Path(home)
    else:
        return Path.home() / default


def cache_dir():
    return _resolve("XDG_CACHE_HOME", ".cache") / "tuxmake"


def config_dir():
    return _resolve("XDG_CONFIG_HOME", ".config") / "tuxmake"
