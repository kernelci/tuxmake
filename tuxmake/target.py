from pathlib import Path
import re
import urllib.request

from tuxmake import __version__
from tuxmake.config import ConfigurableObject, split_commands
from tuxmake.exceptions import InvalidKConfig
from tuxmake.exceptions import UnsupportedTarget
from tuxmake.exceptions import UnsupportedKconfig
from tuxmake.exceptions import UnsupportedKconfigFragment


def supported_targets():
    return Target.supported()


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
        self.runs_after = self.config["target"].get("runs_after", "").split()
        self.preconditions = self.__split_cmds__("target", "preconditions")
        self.commands = self.__split_cmds__("target", "commands")
        try:
            self.artifacts = self.config["artifacts"]
        except KeyError:
            mapping = self.build.target_overrides
            key = mapping[self.name]
            value = self.target_arch.artifacts[self.name].format(**mapping)
            self.artifacts = {key: value}

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return str(self) == str(other)

    def __split_cmds__(self, section, item):
        s = self.config[section].get(item)
        return split_commands(s)

    def prepare(self):
        pass


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
        if self.handle_url(config, conf) or self.handle_local_file(config, conf):
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
                or self.handle_inline_fragment(fragfile, frag)
            ):
                merge.append(str(fragfile))
                self.build.log(f"# {frag} -> {fragfile}")
            elif self.handle_in_tree_config(frag):
                pass
            else:
                raise UnsupportedKconfigFragment(frag)
        if merge:
            self.commands.append(
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
            self.commands.append(["{make}", "olddefconfig"])

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

    def handle_make_target(self, t):
        if re.match(r"^[\w\-]+config$", t):
            self.commands.append(["{make}", t])
            return True
        else:
            return False

    def handle_in_tree_config(self, t):
        if re.match(r"^[\w\-]+.config$", t):
            self.commands.append(["{make}", t])
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


def create_target(name, build):
    cls = __special_targets__.get(name, Target)
    return cls(name, build)
