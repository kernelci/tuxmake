from pathlib import Path
import datetime
import multiprocessing
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
    jobs = multiprocessing.cpu_count() * 2


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

    def run_cmd(self, origcmd):
        cmd = []
        for c in origcmd:
            cmd += self.expand_cmd_part(c)

        final_cmd = self.runtime.get_command_line(cmd)

        self.log(" ".join(cmd))
        process = subprocess.Popen(
            final_cmd,
            cwd=self.source_tree,
            stdin=subprocess.DEVNULL,
            stdout=self.logger.stdin,
            stderr=subprocess.STDOUT,
        )
        try:
            process.communicate()
            return process.returncode == 0
        except KeyboardInterrupt:
            process.terminate()
            sys.exit(1)

    def expand_cmd_part(self, part):
        if part == "{make}":
            return (
                ["make"]
                + self.get_silent()
                + ["--keep-going", f"--jobs={self.jobs}", f"O={self.build_dir}"]
                + self.makevars
            )
        else:
            return [
                part.format(
                    build_dir=self.build_dir,
                    target_arch=self.target_arch.name,
                    toolchain=self.toolchain.name,
                    kconfig=self.kconfig,
                )
            ]

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

        for precondition in target.preconditions:
            if not self.run_cmd(precondition):
                self.status[target.name] = BuildInfo(
                    "SKIP", datetime.timedelta(seconds=0)
                )
                self.log(f"# Skipping {target.name} because precondition failed")
                return

        start = time.time()

        target.prepare()

        status = None
        for cmd in target.commands:
            if not self.run_cmd(cmd):
                status = BuildInfo("FAIL")
                break
        if not status:
            status = BuildInfo("PASS")

        finish = time.time()
        status.duration = datetime.timedelta(seconds=finish - start)

        self.status[target.name] = status

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
