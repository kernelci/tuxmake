from tuxmake.config import ConfigurableObject
from tuxmake.exceptions import UnsupportedToolchain


class Toolchain(ConfigurableObject):
    basedir = "toolchain"
    exception = UnsupportedToolchain

    def __init__(self, name):
        family = name.split("-")[0]
        super().__init__(family)
        self.name = name

    def __init_config__(self):
        self.makevars = self.config["makevars"]
        self.docker_image = self.config["docker"]["image"]

    def expand_makevars(self, arch):
        archvars = {"CROSS_COMPILE": "", **arch.makevars}
        return {
            k: v.format(toolchain=self.name, **archvars)
            for k, v in self.makevars.items()
        }

    def get_docker_image(self, arch):
        return self.docker_image.replace("{toolchain}", self.name).replace(
            "{arch}", arch.name
        )


class NoExplicitToolchain(Toolchain):
    def __init__(self):
        super().__init__("gcc")
        self.makevars = {}
