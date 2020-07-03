from pathlib import Path
import re
import shlex
import urllib.request

from tuxmake.config import ConfigurableObject
from tuxmake.exceptions import UnsupportedTarget


def supported_targets():
    return Target.supported()


def create_target(name, target_arch):
    cls = (name == "config") and Config or Target
    return cls(name, target_arch)


class Target(ConfigurableObject):
    basedir = "target"
    exception = UnsupportedTarget

    def __init__(self, name, target_arch):
        self.target_arch = target_arch
        super().__init__(name)

    def __init_config__(self):
        self.description = self.config["target"].get("description")
        self.dependencies = self.config["target"].get("dependencies", "").split()
        make_args = re.split(r"\s*&&\s*", self.config["target"].get("make_args", ""))
        self.make_args = [shlex.split(c) for c in make_args]
        self.precondition = shlex.split(self.config["target"].get("precondition", ""))
        self.extra_command = shlex.split(self.config["target"].get("extra_command", ""))
        try:
            self.artifacts = self.config["artifacts"]
        except KeyError:
            key = self.target_arch.targets[self.name]
            value = self.target_arch.artifacts[key]
            self.artifacts = {key: value}

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return str(self) == str(other)

    def prepare(self, build):
        pass


class Config(Target):
    def __init_config__(self):
        super().__init_config__()
        self.make_args = []

    def prepare(self, build):
        config = build.build_dir / ".config"
        for conf in build.kconfig:
            if conf.startswith("http://") or conf.startswith("https://"):
                download = urllib.request.urlopen(conf)
                with config.open("a") as f:
                    f.write(download.read().decode("utf-8"))
            elif Path(conf).exists():
                with config.open("a") as f:
                    f.write(Path(conf).read_text())
            else:
                build.make(conf)
