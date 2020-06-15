from configparser import ConfigParser
from pathlib import Path


class Architecture:
    def __init__(self, arch):
        conffile = Path(__file__).parent / "arch" / f"{arch}.ini"
        config = ConfigParser()
        config.optionxform = str
        config.read(conffile)

        self.kernel = config["targets"]["kernel"]
        self.artifacts = config["artifacts"]
