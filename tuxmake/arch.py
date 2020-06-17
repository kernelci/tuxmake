from configparser import ConfigParser
from pathlib import Path
from tuxmake.exceptions import UnsupportedArchitecture


class Architecture:
    def __init__(self, name):
        conffile = Path(__file__).parent / "arch" / f"{name}.ini"
        if not conffile.exists():
            raise UnsupportedArchitecture(name)
        config = ConfigParser()
        config.optionxform = str
        config.read(conffile)

        self.name = name
        self.kernel = config["targets"]["kernel"]
        self.artifacts = config["artifacts"]
        self.makevars = config["makevars"]
