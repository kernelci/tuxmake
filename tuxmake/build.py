from collections import OrderedDict
from pathlib import Path
import datetime
import multiprocessing
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from tuxmake.arch import Architecture, Native
from tuxmake.toolchain import Toolchain, NoExplicitToolchain
from tuxmake.wrapper import Wrapper, NoWrapper
from tuxmake.output import get_new_output_dir
from tuxmake.target import create_target, supported_targets
from tuxmake.runtime import get_runtime
from tuxmake.metadata import MetadataExtractor
from tuxmake.exceptions import UnrecognizedSourceTree


class supported:
    architectures = Architecture.supported()
    targets = supported_targets()
    toolchains = Toolchain.supported()
    runtimes = ["docker"]  # FIXME don't hardcode here
    wrappers = Wrapper.supported()


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
        wrapper=None,
        environment={},
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
        self.wrapper = wrapper and Wrapper(wrapper) or NoWrapper()

        self.environment = environment

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
        self.metadata = OrderedDict()

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
        self.wrapper.prepare()
        self.runtime.prepare()

    def get_silent(self):
        if self.verbose:
            return []
        else:
            return ["--silent"]

    def run_cmd(self, origcmd, output=None):
        cmd = []
        for c in origcmd:
            cmd += self.expand_cmd_part(c)

        final_cmd = self.runtime.get_command_line(cmd)
        env = dict(os.environ, **self.wrapper.environment, **self.environment)

        logger = self.logger.stdin
        if output:
            stdout = subprocess.PIPE
            stderr = logger
        else:
            self.log(" ".join([shlex.quote(c) for c in cmd]))
            stdout = logger
            stderr = subprocess.STDOUT

        process = subprocess.Popen(
            final_cmd,
            cwd=self.source_tree,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
        )
        try:
            out, _ = process.communicate()
            if output:
                output.write(out.decode("utf-8"))
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
                + self.make_args
            )
        else:
            return [self.format_cmd_part(part)]

    def format_cmd_part(self, part):
        return part.format(
            build_dir=self.build_dir,
            target_arch=self.target_arch.name,
            toolchain=self.toolchain.name,
            kconfig=self.kconfig,
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
    def make_args(self):
        return [f"{k}={v}" for k, v in self.makevars.items() if v]

    @property
    def makevars(self):
        mvars = {}
        mvars.update(self.target_arch.makevars)
        mvars.update(self.toolchain.expand_makevars(self.target_arch))
        mvars.update(self.wrapper.wrap(mvars))
        return mvars

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
        return not self.failed

    @property
    def failed(self):
        s = [info.failed for info in self.status.values()]
        return s and True in set(s)

    def extract_metadata(self):
        self.metadata["build"] = {
            "targets": [t.name for t in self.targets],
            "target_arch": self.target_arch.name,
            "toolchain": self.toolchain.name,
            "wrapper": self.wrapper.name,
            "environment": self.environment,
            "kconfig": self.kconfig,
            "kconfig_add": self.kconfig_add,
            "jobs": self.jobs,
            "runtime": self.runtime.name,
            "verbose": self.verbose,
        }
        errors, warnings = self.parse_log()
        self.metadata["results"] = {
            "status": "PASS" if self.passed else "FAIL",
            "targets": {k: s.status for k, s in self.status.items()},
            "artifacts": self.artifacts,
            "errors": errors,
            "warnings": warnings,
        }

        extractor = MetadataExtractor(self)
        self.metadata.update(extractor.extract())

        with (self.output_dir / "metadata.json").open("w") as f:
            f.write(json.dumps(self.metadata, indent=4))
            f.write("\n")

    def parse_log(self):
        errors = 0
        warnings = 0
        for line in (self.output_dir / "build.log").open("r"):
            if "error:" in line:
                errors += 1
            if "warning:" in line:
                warnings += 1
        return errors, warnings

    def terminate(self):
        self.logger.terminate()

    def cleanup(self):
        shutil.rmtree(self.build_dir)

    def run(self):
        self.validate()

        self.prepare()

        for target in self.targets:
            self.build(target)

        for target in self.targets:
            self.copy_artifacts(target)

        self.extract_metadata()

        self.terminate()

        self.cleanup()


def build(tree, **kwargs):
    builder = Build(tree, **kwargs)
    builder.run()
    return builder
