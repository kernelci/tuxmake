import re
from typing import Optional, Type
from configparser import ConfigParser
from pathlib import Path


class ConfigurableObject:
    basedir: Optional[str] = None
    exception: Optional[Type[Exception]] = None

    def __init__(self, name):
        commonconf = Path(__file__).parent / self.basedir / "common.ini"
        conffile = Path(__file__).parent / self.basedir / f"{name}.ini"
        if not conffile.exists():
            raise self.exception(name)
        conffile = conffile.resolve()
        name = conffile.stem
        self.name = name
        self.config = ConfigParser()
        self.config.optionxform = str
        self.config.read(commonconf)
        self.config.read(conffile)
        self.__init_config__()

    def __init_config__(self):
        raise NotImplementedError

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return str(self) == str(other)

    @classmethod
    def supported(cls):
        files = (Path(__file__).parent / cls.basedir).glob("*.ini")
        return [
            str(f.name).replace(".ini", "")
            for f in files
            if f.name != "common.ini" and not f.is_symlink()
        ]


def split(s, sep=r",\s*"):
    if not s:
        return []
    if type(s) is list:
        return s
    result = re.split(sep, s.replace("\n", ""))
    if result[-1] == "":
        result.pop()
    return result


def splitmap(s):
    return {k: v for k, v in [split(pair, ":") for pair in split(s)]}


def splitlistmap(s):
    return {k: split(v, r"\+") for k, v in splitmap(s).items()}
