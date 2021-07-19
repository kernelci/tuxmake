import platform
import re
from tuxmake.config import ConfigurableObject
from tuxmake.exceptions import UnsupportedArchitecture


class Architecture(ConfigurableObject):
    basedir = "arch"
    exception = UnsupportedArchitecture
    config_aliases = {
        "aarch64": "arm64",
        "amd64": "x86_64",
        "armv8l": "arm",
        "i686": "i386",
    }

    def __init_config__(self):
        self.targets = self.config["targets"]
        self.artifacts = self.config["artifacts"]
        self.makevars = self.config["makevars"]
        self.aliases = [k for k, v in self.config_aliases.items() if v == self.name]
        try:
            self.images = self.config["images"]
        except KeyError:
            self.images = {}

    def get_image(self, toolchain):
        for pattern, image in self.images.items():
            if re.match(pattern, toolchain.name):
                return image.format(
                    arch=self.name,
                    toolchain=toolchain.name,
                    version_suffix=toolchain.version_suffix,
                )
        return None


class Native(Architecture):
    def __init__(self):
        name = platform.machine()
        super().__init__(name)
        self.makevars = {}


host_arch = Native()
