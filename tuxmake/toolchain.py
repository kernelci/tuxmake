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
        self.docker_image = self.config["docker"]["image"]
        try:
            self.__compiler__ = self.config["metadata"]["compiler"]
        except KeyError:
            self.__compiler__ = None

    def expand_makevars(self, arch):
        archvars = {"CROSS_COMPILE": "", **arch.makevars}
        return {
            k: v.format(toolchain=self.name, **archvars)
            for k, v in self.makevars.items()
        }

    def get_docker_image(self, arch):
        return self.docker_image.format(
            toolchain=self.name, arch=arch.name, version_suffix=self.version_suffix
        )

    def compiler(self, arch):
        if self.__compiler__:
            return self.__compiler__.format(version_suffix=self.version_suffix)
        else:
            return self.expand_makevars(arch).get("CC")


class NoExplicitToolchain(Toolchain):
    def __init__(self):
        super().__init__("gcc")
        self.makevars = {}

    def compiler(self, arch):
        return arch.makevars.get("CROSS_COMPILE", "") + self.name
