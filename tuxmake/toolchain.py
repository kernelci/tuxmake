import re

from tuxmake.config import ConfigurableObject
from tuxmake.exceptions import UnsupportedToolchain


class Toolchain(ConfigurableObject):
    basedir = "toolchain"
    exception = UnsupportedToolchain
    config_aliases = {"rust": "rustgcc"}

    def __init__(self, name):
        pattern = re.compile(r"((korg-)?(rust|gcc|clang|llvm))-?(.*)")
        match = pattern.search(name)
        family = ""
        version = ""
        if match:
            family = match.group(1)
            version = match.group(4)
        super().__init__(family)
        self.name = name
        if version:
            self.version_suffix = "-" + version
        else:
            self.version_suffix = ""

    def __init_config__(self):
        self.makevars = self.config["makevars"]
        self.image = self.config["docker"]["image"]
        self.__compiler__ = self.config["metadata"]["compiler"]

    def expand_makevars(self, arch):
        archvars = {"CROSS_COMPILE": "", **arch.makevars}
        return {
            k: v.format(toolchain=self.name, **archvars)
            for k, v in self.makevars.items()
        }

    def get_image(self, arch):
        return self.image.format(
            toolchain=self.name, arch=arch.name, version_suffix=self.version_suffix
        )

    def compiler(self, arch, cross_compile=None):
        if not cross_compile:
            cross_compile = arch.makevars.get("CROSS_COMPILE", "")
        return self.__compiler__.format(
            CROSS_COMPILE=cross_compile,
        )

    def suffix(self):
        return self.config["metadata"].get("suffix")


class NoExplicitToolchain(Toolchain):
    def __init__(self):
        super().__init__("gcc")
        self.makevars = {}
