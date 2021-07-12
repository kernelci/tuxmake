from abc import ABC, abstractmethod
import json
import importlib
from pathlib import Path
import shutil
from tuxmake.config import ConfigurableObject
from tuxmake.exceptions import UnsupportedMetadata
from tuxmake.exceptions import UnsupportedMetadataType


class MetadataItemExtactor(ABC):
    def __init__(self, build):
        self.build = build

    def before_build(self):
        """
        This method is called right after the object is created, and gives a
        change for the extractor to collect data before the build is run.
        """

    @abstractmethod
    def get(self):
        """
        This method should return the dedired metadata item. The type must be
        the same as the one declared in the [types] section.
        """


class FreeDiskSpace(MetadataItemExtactor):
    def before_build(self):
        disk_usage = shutil.disk_usage(self.build.build_dir.parent)
        self.free_disk_space = int(disk_usage.free / (2 ** 20))

    def get(self):
        return self.free_disk_space


class MetadataCollector:
    def __init__(self, build, handlers=None):
        self.build = build
        self.handlers = handlers or Metadata.all()
        self.extractors = {}
        self.init_extractors()

    def init_extractors(self):
        for handler in self.handlers:
            self.extractors[handler.name] = {}
            for item, extractor_class in handler.extractor_classes.items():
                self.extractors[handler.name][item] = extractor_class(self.build)

    def each_extractor(self):
        for handler, extractors in self.extractors.items():
            for item, extractor in extractors.items():
                yield handler, item, extractor

    def before_build(self):
        for _, _, extractor in self.each_extractor():
            extractor.before_build()

    def collect(self):
        build = self.build
        compiler = build.toolchain.compiler(build.target_arch)
        metadata_input_data = {
            handler.name: {
                key: build.format_cmd_part(cmd.replace("{compiler}", compiler))
                for key, cmd in handler.commands.items()
            }
            for handler in self.handlers
        }
        metadata_input = build.build_dir / "metadata.in.json"
        metadata_input.write_text(json.dumps(metadata_input_data))

        script_src = Path(__file__).parent / "metadata.pl"
        script = build.build_dir / "metadata.pl"
        shutil.copy(script_src, script)

        stdout = build.build_dir / "extracted-metadata.json"
        with stdout.open("w") as f:
            build.run_cmd(["perl", str(script), str(metadata_input)], stdout=f)
        metadata = self.read_json(stdout.read_text())
        self.collect_extra_metadata(metadata)
        return metadata

    def read_json(self, metadata_json):
        if not metadata_json:
            return {}
        try:
            metadata = json.loads(metadata_json)
        except json.JSONDecodeError:
            return {"invalid_metadata": metadata_json}
        if not metadata:
            return {}

        result = {}
        for handler in self.handlers:
            for key in handler.commands.keys():
                v = metadata[handler.name][key]
                if v:
                    v = v.strip()
                if v:
                    result.setdefault(handler.name, {})
                    result[handler.name][key] = handler.cast(key, v)

        return result

    def collect_extra_metadata(self, metadata):
        for handler, item, extractor in self.each_extractor():
            metadata.setdefault(handler, {})
            metadata[handler][item] = extractor.get()


def linelist(s):
    return s.splitlines()


def get_object(object_ref):
    """
    This is a copy-and-paste from the entry points specification at
    https://packaging.python.org/specifications/entry-points/
    """
    modname, qualname_separator, qualname = object_ref.partition(":")
    obj = importlib.import_module(modname)
    if qualname_separator:
        for attr in qualname.split("."):
            obj = getattr(obj, attr)
    return obj


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
        try:
            self.extractor_classes = {
                name: get_object(_class)
                for name, _class in self.config["extractor_classes"].items()
            }
        except KeyError:
            self.extractor_classes = {}

    def cast(self, key, v):
        t = self.types.get(key, str)
        return t(v)

    @classmethod
    def all(cls):
        return sorted([Metadata(c) for c in cls.supported()], key=lambda m: m.order)
