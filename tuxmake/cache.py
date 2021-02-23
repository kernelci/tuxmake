import shelve
from tuxmake.xdg import cache_dir


def __cache__():
    cache = cache_dir() / "cache"
    cache.parent.mkdir(parents=True, exist_ok=True)
    return str(cache)


def __key__(k):
    return "/".join(k)


def set(key, value):
    with shelve.open(__cache__()) as db:
        db[__key__(key)] = value


def get(key):
    with shelve.open(__cache__()) as db:
        return db.get(__key__(key))
