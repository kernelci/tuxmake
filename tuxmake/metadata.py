from io import StringIO
import json
from pathlib import Path
import shutil
from tuxmake.config import ConfigurableObject
from tuxmake.exceptions import UnsupportedMetadata
from tuxmake.exceptions import UnsupportedMetadataType


class MetadataExtractor:
    def __init__(self, build):
        self.build = build

    def extract(self):
        handlers = Metadata.all()
        build = self.build
        compiler = build.toolchain.compiler(build.target_arch)
        metadata_input_data = {
            handler.name: {
                key: build.format_cmd_part(cmd.replace("{compiler}", compiler))
                for key, cmd in handler.commands.items()
            }
            for handler in handlers
        }
        metadata_input = build.build_dir / "metadata.in.json"
        metadata_input.write_text(json.dumps(metadata_input_data))

        script_src = Path(__file__).parent / "metadata.pl"
        script = build.build_dir / "metadata.pl"
        shutil.copy(script_src, script)

        stdout = StringIO()
        build.run_cmd(["perl", str(script), str(metadata_input)], output=stdout)
        stdout.seek(0)
        metadata_json = stdout.read()
        metadata = json.loads(metadata_json)

        result = {}
        for handler in handlers:
            for key in handler.commands.keys():
                v = metadata[handler.name][key]
                if v:
                    v = v.strip()
                if v:
                    result.setdefault(handler.name, {})
                    result[handler.name][key] = handler.cast(key, v)

        return result


def linelist(s):
    return s.splitlines()


class Metadata(ConfigurableObject):
    basedir = "metadata"
    exception = UnsupportedMetadata
    order = 0

    def __init_config__(self):
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
        self.commands = dict(self.config["commands"])

    def cast(self, key, v):
        t = self.types.get(key, str)
        return t(v)

    @classmethod
    def all(cls):
        return sorted([Metadata(c) for c in cls.supported()], key=lambda m: m.order)
