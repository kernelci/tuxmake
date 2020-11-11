from tuxmake.config import ConfigurableObject
from tuxmake.exceptions import UnsupportedToolchain


class Toolchain(ConfigurableObject):
    basedir = "toolchain"
    exception = UnsupportedToolchain

    def __init__(self, name):
        parts = name.split("-")
        family = parts[0]
        super().__init__(family)
        self.name = name
        if len(parts) > 1:
            self.version_suffix = "-" + parts[1]
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

    def compiler(self, arch):
        return self.__compiler__.format(
            CROSS_COMPILE=arch.makevars.get("CROSS_COMPILE", "")
        )


class NoExplicitToolchain(Toolchain):
    def __init__(self):
        super().__init__("gcc")
        self.makevars = {}
