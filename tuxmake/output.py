from pathlib import Path
import os


def get_default_output_basedir():
    base = os.getenv("XDG_CACHE_HOME")
    if base:
        return Path(base) / "tuxmake" / "builds"
    else:
        return Path.home() / ".cache" / "tuxmake" / "builds"


def get_new_output_dir():
    base = get_default_output_basedir()
    base.mkdir(parents=True, exist_ok=True)
    existing = [int(f.name) for f in base.glob("[0-9]*")]
    if existing:
        new = max(existing) + 1
    else:
        new = 1
    while True:
        new_dir = base / str(new)
        try:
            new_dir.mkdir()
            break
        except FileExistsError:
            new += 1
    return new_dir
