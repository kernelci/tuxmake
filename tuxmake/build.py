from pathlib import Path
import datetime
import os
import shlex
import shutil
import subprocess
import sys
import time
from tuxmake.arch import Architecture, Native
from tuxmake.toolchain import Toolchain, NoExplicitToolchain
from tuxmake.output import get_new_output_dir
from tuxmake.target import create_target, supported_targets
from tuxmake.runtime import get_runtime
from tuxmake.exceptions import UnrecognizedSourceTree


class supported:
    architectures = Architecture.supported()
    targets = supported_targets()
    toolchains = Toolchain.supported()
    runtimes = ["docker"]  # FIXME don't hardcode here


class defaults:
    kconfig = "defconfig"
    targets = ["config", "kernel", "modules", "dtbs"]
    jobs = int(subprocess.check_output(["nproc"], text=True)) * 2


class BuildInfo:
    def __init__(self, status, duration=None):
        self.status = status
        self.duration = duration

    @property
    def failed(self):
        return self.status == "FAIL"

    @property
    def passed(self):
        return self.status == "PASS"

    @property
    def skipped(self):
        return self.status == "SKIP"


class Build:
    def __init__(
        self,
        source_tree,
        *,
        output_dir=None,
        target_arch=None,
        toolchain=None,
        kconfig=defaults.kconfig,
        kconfig_add=[],
        targets=defaults.targets,
        jobs=defaults.jobs,
        runtime=None,
        verbose=False,
    ):
        self.source_tree = source_tree

        if output_dir is None:
            self.output_dir = get_new_output_dir()
        else:
            self.output_dir = output_dir
            os.mkdir(self.output_dir)

        self.build_dir = self.output_dir / "tmp"
        os.mkdir(self.build_dir)

        self.target_arch = target_arch and Architecture(target_arch) or Native()
        self.toolchain = toolchain and Toolchain(toolchain) or NoExplicitToolchain()

        self.kconfig = kconfig
        self.kconfig_add = kconfig_add

        self.targets = []
        for t in targets:
            self.add_target(t)

        self.jobs = jobs

        self.runtime = get_runtime(self, runtime)

        self.verbose = verbose

        self.artifacts = ["build.log"]
        self.__logger__ = None
        self.status = {}

    def add_target(self, target_name):
        target = create_target(target_name, self)
        for d in target.dependencies:
            self.add_target(d)
        if target not in self.targets:
            self.targets.append(target)

    def validate(self):
        source = Path(self.source_tree)
        files = [str(f.name) for f in source.glob("*")]
        if "Makefile" in files and "Kconfig" in files and "Kbuild" in files:
            return
        raise UnrecognizedSourceTree(source.absolute())

    def prepare(self):
        self.log(
            "# command line: "
            + " ".join(["tuxmake"] + [shlex.quote(a) for a in sys.argv[1:]])
        )
        self.runtime.prepare()

    def get_silent(self):
        if self.verbose:
            return []
        else:
            return ["--silent"]

    def make(self, *args):
        cmd = (
            ["make"]
            + self.get_silent()
            + ["--keep-going", f"--jobs={self.jobs}", f"O={self.build_dir}"]
            + self.makevars
            + list(args)
        )
        self.run_cmd(cmd)

    def run_cmd(self, cmd):
        cmd = [
            c.format(build_dir=self.build_dir, target_arch=self.target_arch.name)
            for c in cmd
        ]

        final_cmd = self.runtime.get_command_line(cmd)

        self.log(" ".join(cmd))
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
        return [f"{k}={v}" for k, v in self.environment.items() if v]

    @property
    def environment(self):
        v = {}
        v.update(self.target_arch.makevars)
        v.update(self.toolchain.expand_makevars(self.target_arch))
        return v

    def build(self, target):
        for dep in target.dependencies:
            if not self.status[dep].passed:
                self.status[target.name] = BuildInfo(
                    "SKIP", datetime.timedelta(seconds=0)
                )
                return

        try:
            for precondition in target.preconditions:
                self.run_cmd(precondition)
        except subprocess.CalledProcessError:
            self.status[target.name] = BuildInfo("SKIP", datetime.timedelta(seconds=0))
            self.log(f"# Skipping {target.name} because precondition failed")
            return

        start = time.time()
        try:
            target.prepare()
            for args in target.make_args:
                self.make(*args)
            for cmd in target.extra_commands:
                self.run_cmd(cmd)
            self.status[target.name] = BuildInfo("PASS")
        except subprocess.CalledProcessError:
            self.status[target.name] = BuildInfo("FAIL")
        finish = time.time()
        self.status[target.name].duration = datetime.timedelta(seconds=finish - start)

    def copy_artifacts(self, target):
        if not self.status[target.name].passed:
            return
        for origdest, origsrc in target.artifacts.items():
            dest = self.output_dir / origdest
            src = self.build_dir / origsrc
            shutil.copy(src, Path(self.output_dir / dest))
            self.artifacts.append(origdest)

    @property
    def passed(self):
        s = [info.passed for info in self.status.values()]
        return s and True not in set(s)

    @property
    def failed(self):
        s = [info.failed for info in self.status.values()]
        return s and True in set(s)

    def cleanup(self):
        self.logger.terminate()
        shutil.rmtree(self.build_dir)

    def run(self):
        self.validate()

        self.prepare()

        for target in self.targets:
            self.build(target)

        for target in self.targets:
            self.copy_artifacts(target)

        self.cleanup()


def build(tree, **kwargs):
    builder = Build(tree, **kwargs)
    builder.run()
    return builder
