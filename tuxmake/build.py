from pathlib import Path
import datetime
import os
import shutil
import subprocess
import time
from urllib.request import urlopen
from tuxmake.arch import Architecture
from tuxmake.toolchain import Toolchain
from tuxmake.output import get_new_output_dir
from tuxmake.runner import get_runner
from tuxmake.exceptions import UnsupportedTarget


class defaults:
    target_arch = subprocess.check_output(["uname", "-m"], text=True).strip()
    toolchain = "gcc"
    kconfig = ["defconfig"]
    targets = ["config", "kernel"]
    jobs = int(subprocess.check_output(["nproc"], text=True)) * 2


class BuildInfo:
    def __init__(self, status, duration=None):
        self.status = status
        self.duration = duration

    @property
    def fail(self):
        return self.status == "FAIL"


class Build:
    def __init__(self, source_tree, build_dir, output_dir):
        self.source_tree = source_tree
        self.build_dir = build_dir
        self.output_dir = output_dir
        self.arch = Architecture(defaults.target_arch)
        self.toolchain = Toolchain(defaults.toolchain)
        self.kconfig = defaults.kconfig
        self.jobs = defaults.jobs
        self.artifacts = ["build.log"]
        self.__logger__ = None
        self.status = {}

    def make(self, *args):
        cmd = (
            ["make", "--silent", f"--jobs={self.jobs}", f"O={self.build_dir}"]
            + self.makevars
            + list(args)
        )
        self.log(" ".join(cmd))
        self.run(cmd)

    def run(self, cmd):
        runner = get_runner(self)
        final_cmd = runner.get_command_line(cmd)
        subprocess.check_call(
            final_cmd,
            cwd=self.source_tree,
            stdout=self.logger.stdin,
            stderr=subprocess.STDOUT,
        )

    @property
    def logger(self):
        if not self.__logger__:
            self.__logger__ = subprocess.Popen(
                ["tee", str(self.output_dir / "build.log")], stdin=subprocess.PIPE
            )
        return self.__logger__

    def log(self, *stuff):
        subprocess.call(["echo"] + list(stuff), stdout=self.logger.stdin)

    @property
    def makevars(self):
        return [f"{k}={v}" for k, v in self.environment.items()]

    @property
    def environment(self):
        v = {}
        v.update(self.arch.makevars)
        v.update(self.toolchain.expand_makevars(self.arch))
        return v

    def build(self, target):
        start = time.time()
        try:
            if target == "config":
                config = self.build_dir / ".config"
                for conf in self.kconfig:
                    if conf.startswith("http://") or conf.startswith("https://"):
                        download = urlopen(conf)
                        with config.open("a") as f:
                            f.write(download.read().decode("utf-8"))
                    elif Path(conf).exists():
                        with config.open("a") as f:
                            f.write(Path(conf).read_text())
                    else:
                        self.make(conf)
            elif target == "kernel":
                self.make()
            else:
                raise UnsupportedTarget(target)
            self.status[target] = BuildInfo("PASS")
        except subprocess.CalledProcessError:
            self.status[target] = BuildInfo("FAIL")
        finish = time.time()
        self.status[target].duration = datetime.timedelta(seconds=finish - start)

    def copy_artifacts(self, target):
        if self.status[target].fail:
            return
        if target == "kernel":
            dest = self.arch.kernel
        else:
            dest = target
        src = self.build_dir / self.arch.artifacts[dest]
        shutil.copy(src, Path(self.output_dir / dest))
        self.artifacts.append(dest)

    @property
    def passed(self):
        s = [info.fail for info in self.status.values()]
        return s and True not in set(s)

    @property
    def failed(self):
        s = [info.fail for info in self.status.values()]
        return s and True in set(s)

    def cleanup(self):
        self.logger.terminate()
        shutil.rmtree(self.build_dir)


def build(
    tree,
    *,
    target_arch=defaults.target_arch,
    toolchain=defaults.toolchain,
    kconfig=defaults.kconfig,
    targets=defaults.targets,
    jobs=defaults.jobs,
    output_dir=None,
):

    if output_dir is None:
        output_dir = get_new_output_dir()
    else:
        os.mkdir(output_dir)

    tmpdir = output_dir / "tmp"
    os.mkdir(tmpdir)

    builder = Build(tree, tmpdir, output_dir)
    builder.arch = Architecture(target_arch)
    builder.toolchain = Toolchain(toolchain)
    builder.kconfig = kconfig
    builder.jobs = jobs

    for target in targets:
        builder.build(target)

    for target in targets:
        builder.copy_artifacts(target)

    builder.cleanup()

    return builder
