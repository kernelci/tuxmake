from configparser import ConfigParser
from pathlib import Path
from tuxmake.exceptions import UnsupportedArchitecture


class Architecture:
    def __init__(self, name):
        commonconf = Path(__file__).parent / "arch" / "common.ini"
        conffile = Path(__file__).parent / "arch" / f"{name}.ini"
        if not conffile.exists():
            raise UnsupportedArchitecture(name)
        config = ConfigParser()
        config.optionxform = str
        config.read(commonconf)
        config.read(conffile)

        self.name = name
        self.kernel = config["targets"]["kernel"]
        self.debugkernel = config["targets"]["debugkernel"]
        self.artifacts = config["artifacts"]
        self.makevars = config["makevars"]
