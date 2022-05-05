from typing import List, Tuple

from pathlib import Path
import re
import shlex
import urllib.request

from tuxmake import __version__
from tuxmake.config import ConfigurableObject, split_commands
from tuxmake.exceptions import InvalidKConfig
from tuxmake.exceptions import UnsupportedCompression
from tuxmake.exceptions import UnsupportedTarget
from tuxmake.exceptions import UnsupportedKconfig
from tuxmake.exceptions import UnsupportedKconfigFragment


def supported_targets():
    return Target.supported()


class Command(list):
    interactive = False


class compression_types:
    class xz:
        command = ["xz", "-T0", "--force", "--keep"]
        extension = ".xz"

    class none:
        command = ["true"]
        extension = ""


class Compression:
    supported: List[str] = [
        c for c in compression_types.__dict__ if not c.startswith("_")
    ]

    def __init__(self, ctype=None):
        if ctype is None:
            ctype = "xz"
        try:
            self.__type__ = getattr(compression_types, ctype)
        except AttributeError:
            raise UnsupportedCompression(ctype)

    def format(self, s) -> str:
        return s.format(z_ext=self.extension)

    @property
    def name(self) -> str:
        return self.__type__.__name__

    @property
    def extension(self) -> str:
        return self.__type__.extension

    @property
    def command(self) -> List[str]:
        return self.__type__.command


default_compression = Compression()


class Target(ConfigurableObject):
    basedir = "target"
    exception = UnsupportedTarget

    def __init__(self, name, build, compression=default_compression):
        self.build = build
        self.compression = compression
        self.target_arch = build.target_arch
        super().__init__(name)

    def __init_config__(self):
        self.description = self.config["target"].get("description")
        self.dependencies = self.config["target"].get("dependencies", "").split()
        self.runs_after = self.config["target"].get("runs_after", "").split()
        self.preconditions = self.__split_cmds__("target", "preconditions")
        self.commands = self.__split_cmds__("target", "commands")
        self.kconfig_add = self.__split_kconfigs__()
        try:
            artifacts = dict(self.config["artifacts"])
            self.artifacts = {}
            for k, v in artifacts.items():
                key = self.compression.format(k)
                value = self.compression.format(v)
                self.artifacts[key] = value
        except KeyError:
            mapping = self.build.target_overrides
            if mapping and self.name in mapping:
                key = mapping[self.name]
                value = self.target_arch.artifacts[self.name].format(**mapping)
                self.artifacts = {key: value}
            else:
                self.artifacts = {}
        try:
            self.makevars = dict(self.config["makevars"])
        except KeyError:
            self.makevars = {}

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return str(self) == str(other)

    def __split_cmds__(self, section, item):
        s = self.config[section].get(item)
        return [Command(c) for c in split_commands(s)]

    def add_command(self, cmd):
        c = Command(cmd)
        self.commands.append(c)
        return c

    def prepare(self):
        pass

    def find_artifacts(self, build_dir: Path) -> List[Tuple[str, Path]]:
        results = []
        for dest, src in self.artifacts.items():
            expanded_glob = list(build_dir.glob(src))
            if not expanded_glob:
                results.append((dest, build_dir / src))
                continue
            for path in expanded_glob:
                if dest == src and "*" in dest:
                    d = path.name
                else:
                    d = dest
                results.append((d, path))
        return results

    def __split_kconfigs__(self):
        s = self.config["target"].get("kconfig_add", "")
        return shlex.split(s)


class Config(Target):
    def __init_config__(self):
        super().__init_config__()

    def prepare(self):
        olddefconfig = False
        build_dir = self.build.build_dir
        config = build_dir / ".config"
        conf = self.build.kconfig
        if config.exists():
            return
        if (
            self.handle_url(config, conf)
            or self.handle_local_file(config, conf)
            or self.handle_in_tree_file(config, conf)
        ):
            self.build.log(f"# {conf} -> {config}")
            olddefconfig = True
        elif self.handle_make_target(conf):
            pass
        else:
            raise UnsupportedKconfig(conf)

        kconfig_add = self.build.kconfig_add
        if not kconfig_add:
            return

        merge = []
        for i in range(len(kconfig_add)):
            frag = kconfig_add[i]
            fragfile = build_dir / f"{i}.config"
            if (
                self.handle_url(fragfile, frag)
                or self.handle_local_file(fragfile, frag)
                or self.handle_in_tree_file(fragfile, frag)
                or self.handle_inline_fragment(fragfile, frag)
            ):
                merge.append(str(fragfile))
                self.build.log(f"# {frag} -> {fragfile}")
            elif self.handle_in_tree_config(frag):
                pass
            elif self.handle_explicit_make_target(frag):
                pass
            else:
                raise UnsupportedKconfigFragment(frag)
        if merge:
            self.add_command(
                [
                    "scripts/kconfig/merge_config.sh",
                    "-m",
                    "-O",
                    str(build_dir),
                    str(config),
                    *merge,
                ]
            )
            olddefconfig = True
        if olddefconfig:
            self.add_command(["{make}", "olddefconfig"])

    def handle_url(self, config, url):
        if not url.startswith("http://") and not url.startswith("https://"):
            return False

        header = {"User-Agent": "tuxmake/{}".format(__version__)}
        try:
            req = urllib.request.Request(url, headers=header)
            download = urllib.request.urlopen(req)
        except urllib.error.URLError as error:
            raise InvalidKConfig(f"{url} - {error}")
        with config.open("w") as f:
            f.write(download.read().decode("utf-8"))
        return True

    def handle_local_file(self, config, filename):
        path = Path(filename)
        if not path.exists():
            return False

        with config.open("w") as f:
            f.write(path.read_text())
        return True

    def handle_in_tree_file(self, config, filename):
        path = self.build.source_tree / filename
        if not path.exists():
            return False

        with config.open("w") as f:
            f.write(path.read_text())
        return True

    def handle_make_target(self, t):
        if re.match(r"^[\w\-]+config$", t):
            self.add_command(["{make}", t])
            return True
        else:
            return False

    def handle_explicit_make_target(self, t):
        if re.match(r"^make:.*$", t):
            target = re.sub(r"^make:", "", t)
            self.add_command(["{make}", target])
            return True
        elif re.match(r"^imake:.*$", t):
            target = re.sub(r"^imake:", "", t)
            self.add_command(["{make}", target]).interactive = True
            return True
        else:
            return False

    def handle_in_tree_config(self, t):
        if re.match(r"^[\w\-]+.config$", t):
            self.add_command(["{make}", t])
            return True
        else:
            return False

    def handle_inline_fragment(self, config, frag):
        accepted_patterns = [
            r"^CONFIG_\w+=[ymn]$",
            r"^#\s*CONFIG_\w+\s*is\s*not\s*set\s*$",
        ]
        accepted = False
        for pattern in accepted_patterns:
            if re.match(pattern, frag):
                accepted = True

        if not accepted:
            return False

        with config.open("a") as f:
            f.write(frag)
            f.write("\n")
        return True


class Kernel(Target):
    def __init_config__(self):
        super().__init_config__()
        if "vmlinux" in self.artifacts:
            self.artifacts["vmlinux"] = "vmlinux"


__special_targets__ = {"config": Config, "kernel": Kernel}


def create_target(name, build, compression=default_compression):
    cls = __special_targets__.get(name, Target)
    return cls(name, build, compression)
