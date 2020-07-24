import os
from pathlib import Path
from tuxmake.config import ConfigurableObject
from tuxmake.exceptions import UnsupportedWrapper


def expand(k, s):
    v = os.getenv(k)
    if not v:
        v = Path(s).expanduser()
    return str(v)


class Wrapper(ConfigurableObject):
    basedir = "wrapper"
    exception = UnsupportedWrapper
    path = None

    def __init__(self, name):
        if name.startswith("/"):
            self.path = name
            name = str(Path(name).name)
        super().__init__(name)

    def __init_config__(self):
        self.environment = {
            k: expand(k, v) for k, v in self.config["environment"].items()
        }

    def prepare(self):
        for k, v in self.environment.items():
            if k.endswith("_DIR"):
                Path(v).mkdir(parents=True, exist_ok=True)

    def wrap(self, makevars):
        return {
            k: f"{self.name} {v}" for k, v in makevars.items() if k in ("CC", "HOSTCC")
        } or {"CC": f"{self.name} gcc", "HOSTCC": f"{self.name} gcc"}


class NoWrapper(Wrapper):
    def __init__(self):
        self.environment = {}

    def prepare(self):
        pass

    def wrap(self, makevars):
        return {}
