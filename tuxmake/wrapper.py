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
        self.prepare_cmds = split_commands(self.config["commands"].get("prepare", ""))
        self.command = self.config["commands"].get("wrapper")

    def prepare_host(self):
        for k, v in self.environment.items():
            if k.endswith("_DIR"):
                Path(v).mkdir(parents=True, exist_ok=True)

    def prepare_runtime(self, build):
        for cmd in self.prepare_cmds:
            build.run_cmd(cmd, echo=False, stdout=subprocess.DEVNULL)

    def wrap(self, makevars):
        if not self.command:
            return makevars
        cross = makevars.get("CROSS_COMPILE", "")
        llvm = makevars.get("LLVM")
        if llvm:
            if llvm.startswith("-"):
                compiler = f"clang{llvm}"
            elif llvm.endswith("/"):
                compiler = f"{llvm}clang"
            else:
                compiler = "clang"
            return {
                "CC": f"{self.command} {compiler}",
                "HOSTCC": f"{self.command} {compiler}",
            }
        compilers = {
            "CC": makevars.get("CC") or f"{cross}gcc",
            "HOSTCC": makevars.get("HOSTCC") or "gcc",
        }
        return {k: f"{self.command} {v}" for k, v in compilers.items()}
