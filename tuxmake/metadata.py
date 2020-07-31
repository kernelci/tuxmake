from io import StringIO
from tuxmake.config import ConfigurableObject
from tuxmake.exceptions import UnsupportedMetadata
from tuxmake.exceptions import UnsupportedMetadataType


class MetadataExtractor:
    def __init__(self, build):
        self.build = build

    def extract(self):
        result = {}
        for handler in Metadata.all():
            metadata = handler.extract(self.build)
            if metadata:
                result.update(metadata)
        return result


def linelist(s):
    return s.splitlines()


class Metadata(ConfigurableObject):
    basedir = "metadata"
    exception = UnsupportedMetadata
    order = 0

    def __init_config__(self):
        self.commands = []
        self.types = {}
        try:
            self.order = int(self.config["meta"]["order"])
        except KeyError:
            pass  # no order, use default
        try:
            for k, t in self.config["types"].items():
                if t not in ["int", "str", "linelist"]:
                    raise UnsupportedMetadataType(t)
                self.types[k] = eval(t)
        except KeyError:
            pass  # no types, assume everything is str

        for key, cmd in self.config["commands"].items():
            self.commands.append((key, cmd))

    def extract(self, build):
        output = {}

        compiler = build.toolchain.compiler(build.target_arch)
        for key, cmd in self.commands:
            cmd = cmd.replace("{compiler}", compiler)
            stdout = StringIO()
            if build.run_cmd(["sh", "-c", cmd], output=stdout):
                stdout.seek(0)
                v = stdout.read().strip()
                if v:
                    output[key] = self.cast(key, v)
        if output:
            return {self.name: output}

    def cast(self, key, v):
        t = self.types.get(key, str)
        return t(v)

    @classmethod
    def all(cls):
        return sorted([Metadata(c) for c in cls.supported()], key=lambda m: m.order)
