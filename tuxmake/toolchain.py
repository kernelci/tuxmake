from pathlib import Path
import re

from tuxmake.config import ConfigurableObject
from tuxmake.exceptions import UnsupportedToolchain


class Toolchain(ConfigurableObject):
    basedir = "toolchain"
    exception = UnsupportedToolchain
    config_aliases = {"rust": "rustgcc"}

    def __init__(self, name):
        pattern = re.compile(r"((korg-)?(rust|gcc|clang))-?(.*)")
        match = pattern.search(name)
        family = ""
        version = ""
        if match:
            family = match.group(1)
            version = match.group(4)

        # Try to load config for full name first, fall back to family
        config_name = family
        full_name_config = Path(__file__).parent / self.basedir / f"{name}.ini"
        if full_name_config.exists():
            config_name = name

        super().__init__(config_name)
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
        # Start with base makevars
        result = {
            k: v.format(toolchain=self.name, **archvars)
            for k, v in self.makevars.items()
        }
        # Override with architecture-specific makevars if they exist
        arch_section = f"makevars:{arch.name}"
        if self.config.has_section(arch_section):
            arch_specific = {
                k: v.format(toolchain=self.name, **archvars)
                for k, v in self.config[arch_section].items()
            }
            result.update(arch_specific)
        return result

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
