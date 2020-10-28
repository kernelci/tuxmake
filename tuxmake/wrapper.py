import os
import subprocess
from pathlib import Path
from tuxmake.config import ConfigurableObject, split_commands
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
        self.prepare_cmds = split_commands(self.config["commands"]["prepare"])

    def prepare(self, build):
        for k, v in self.environment.items():
            if k.endswith("_DIR"):
                Path(v).mkdir(parents=True, exist_ok=True)
        for cmd in self.prepare_cmds:
            build.run_cmd(cmd, stdout=subprocess.DEVNULL)

    def wrap(self, makevars):
        cross = makevars.get("CROSS_COMPILE", "")
        if makevars.get("LLVM") == "1":
            return {"CC": f"{self.name} clang", "HOSTCC": f"{self.name} clang"}
        return {
            k: f"{self.name} {v}" for k, v in makevars.items() if k in ("CC", "HOSTCC")
        } or {"CC": f"{self.name} {cross}gcc", "HOSTCC": f"{self.name} gcc"}


class NoWrapper(Wrapper):
    def __init__(self):
        self.environment = {}
        self.name = "none"

    def prepare(self, build):
        pass

    def wrap(self, makevars):
        return {}
