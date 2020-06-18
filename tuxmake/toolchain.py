from configparser import ConfigParser
from pathlib import Path
from tuxmake.exceptions import UnsupportedToolchain


class Toolchain:
    def __init__(self, name):
        family = name.split("-")[0]
        conffile = Path(__file__).parent / "toolchain" / f"{family}.ini"
        if not conffile.exists():
            raise UnsupportedToolchain(name)
        config = ConfigParser()
        config.optionxform = str
        config.read(conffile)

        self.name = name
        self.makevars = config["makevars"]

    def expand_makevars(self, arch):
        return {
            k: v.format(toolchain=self.name, **arch.makevars)
            for k, v in self.makevars.items()
        }
