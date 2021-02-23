from tuxmake import xdg


def get_default_output_basedir():
    return xdg.cache_dir() / "builds"


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
