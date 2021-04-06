import re
import shlex
from functools import lru_cache
from typing import Type, Dict, List, Tuple, Union
from configparser import ConfigParser as OrigConfigParser
from pathlib import Path


class ConfigParser(OrigConfigParser):
    def optionxform(self, opt):
        return str(opt)


class ConfigurableObject:
    basedir: str = "config"
    exception: Type[Exception] = RuntimeError
    config_aliases: Dict[str, str] = {}

    def __init__(self, name: str):
        self.name, self.config = self.read_config(name)
        self.__init_config__()

    @classmethod
    @lru_cache(None)
    def read_config(cls, name: str) -> Tuple[str, ConfigParser]:
        commonconf = Path(__file__).parent / cls.basedir / "common.ini"
        conffile = Path(__file__).parent / cls.basedir / f"{name}.ini"
        if not conffile.exists():
            raise cls.exception(name)
        name = cls.config_aliases.get(conffile.stem, name)
        config = ConfigParser()
        config.read(commonconf)
        config.read(conffile)
        return name, config

    def __init_config__(self) -> None:
        raise NotImplementedError

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other) -> bool:
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(self.name)

    @classmethod
    def supported(cls) -> List[str]:
        files = (Path(__file__).parent / cls.basedir).glob("*.ini")
        return [
            str(f.name).replace(".ini", "")
            for f in files
            if f.name != "common.ini" and f.stem not in cls.config_aliases
        ]


def split(s: Union[str, List[str]], sep: str = r",\s*") -> List[str]:
    if not s:
        return []
    if type(s) is list:
        return list(s)
    s = str(s)
    result = re.split(sep, s.replace("\n", ""))
    if result[-1] == "":
        result.pop()
    return result


def splitmap(s: str) -> dict:
    return {k: v for k, v in [split(pair, ":") for pair in split(s)]}


def splitlistmap(s: str) -> Dict[str, list]:
    return {k: split(v, r"\+") for k, v in splitmap(s).items()}


def split_commands(s: str) -> List[List[str]]:
    if not s:
        return []
    result: List[List[str]] = [[]]
    for item in shlex.split(s):
        if item == "&&":
            result.append([])
        else:
            result[-1].append(item)
    return result
