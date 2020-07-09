from pathlib import Path
import re
import shlex
import urllib.request

from tuxmake.config import ConfigurableObject
from tuxmake.exceptions import InvalidKConfig
from tuxmake.exceptions import UnsupportedTarget
from tuxmake.exceptions import UnsupportedKconfig
from tuxmake.exceptions import UnsupportedKconfigFragment


def supported_targets():
    return Target.supported()


def create_target(name, build):
    cls = (name == "config") and Config or Target
    return cls(name, build)


class Target(ConfigurableObject):
    basedir = "target"
    exception = UnsupportedTarget

    def __init__(self, name, build):
        self.build = build
        self.target_arch = build.target_arch
        super().__init__(name)

    def __init_config__(self):
        self.description = self.config["target"].get("description")
        self.dependencies = self.config["target"].get("dependencies", "").split()
        self.make_args = self.__split_cmds__("target", "make_args") or [[]]
        self.preconditions = self.__split_cmds__("target", "preconditions")
        self.extra_commands = self.__split_cmds__("target", "extra_commands")
        try:
            self.artifacts = self.config["artifacts"]
        except KeyError:
            key = self.target_arch.targets[self.name]
            value = self.target_arch.artifacts[key]
            self.artifacts = {key: value}

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return str(self) == str(other)

    def __split_cmds__(self, section, item):
        s = self.config[section].get(item)
        if not s:
            return []
        result = [[]]
        for item in shlex.split(s):
            if item == "&&":
                result.append([])
            else:
                result[-1].append(item)
        return result

    def prepare(self):
        pass


class Config(Target):
    def __init_config__(self):
        super().__init_config__()
        self.make_args = []

    def prepare(self):
        build_dir = self.build.build_dir
        config = build_dir / ".config"
        conf = self.build.kconfig
        if not self.handle_url(config, conf):
            if not self.handle_local_file(config, conf):
                if not self.handle_make_target(conf):
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
                or self.handle_inline_fragment(fragfile, frag)
            ):
                merge.append(str(fragfile))
                self.build.log(f"# {frag} -> {fragfile}")
            elif self.handle_in_tree_config(frag):
                pass
            else:
                raise UnsupportedKconfigFragment(frag)
        if merge:
            self.build.run_cmd(
                [
                    "scripts/kconfig/merge_config.sh",
                    "-m",
                    "-O",
                    str(build_dir),
                    str(config),
                    *merge,
                ]
            )
            self.build.make("olddefconfig")

    def handle_url(self, config, url):
        if not url.startswith("http://") and not url.startswith("https://"):
            return False

        try:
            download = urllib.request.urlopen(url)
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

    def handle_make_target(self, t):
        if re.match(r"^\w+config$", t):
            self.build.make(t)
            return True
        else:
            return False

    def handle_in_tree_config(self, t):
        if re.match(r"^\w+\.config$", t):
            self.build.make(t)
            return True
        else:
            return False

    def handle_inline_fragment(self, config, frag):
        if not re.match(r"^CONFIG_\w+=[ym]$", frag) and not re.match(
            r"^#\s*CONFIG_\w+\s*is\s*not\s*set\s*$", frag
        ):
            return False

        with config.open("a") as f:
            f.write(frag)
            f.write("\n")
        return True
