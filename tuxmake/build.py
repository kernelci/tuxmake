from contextlib import contextmanager
from collections import OrderedDict
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import time
from tuxmake import __version__
from tuxmake.arch import Architecture, host_arch
from tuxmake.toolchain import Toolchain, NoExplicitToolchain
from tuxmake.wrapper import Wrapper
from tuxmake.output import get_new_output_dir
from tuxmake.target import create_target
from tuxmake.runtime import get_runtime
from tuxmake.metadata import MetadataExtractor
from tuxmake.exceptions import UnrecognizedSourceTree
from tuxmake.exceptions import UnsupportedArchitectureToolchainCombination
from tuxmake.exceptions import UnsupportedMakeVariable
from tuxmake.log import LogParser
from tuxmake.cmdline import CommandLine
from tuxmake.utils import defaults
from tuxmake.utils import quote_command_line


class BuildInfo:
    """
    Instances of this class represent the build results of each target (see
    `Build.status`).
    """

    def __init__(self, status, duration=None):
        self.__status__ = status
        self.__duration__ = duration

    @property
    def status(self):
        """
        The target build status. `"PASS"`, `"FAIL"`, or `"SKIP"`.
        """
        return self.__status__

    @property
    def duration(self):
        """
        Time this target took to build; a `float`, representing the duration in
        seconds.
        """
        return self.__duration__

    @duration.setter
    def duration(self, d):
        self.__duration__ = d

    @property
    def failed(self):
        """
        `True` if this target failed.
        """
        return self.status == "FAIL"

    @property
    def passed(self):
        """
        `True` if this target passed.
        """
        return self.status == "PASS"

    @property
    def skipped(self):
        """
        `True` if this target was skipped.
        """
        return self.status == "SKIP"


class Build:
    """
    This class encapsulates a tuxmake build.

    The class constructor takes in more or less the same parameters as the the
    command line API, and will raise an exception if any of the arguments, or
    combinarion of them, is not supported. For example, if you want to only
    validate a set of build arguments, but not actually run the build, you can
    just instantiate this class.

    Only the methods and properties that are documented here can be considered
    as the public API of this class. All other methods must be considered as
    implementation details.

    All constructor parameters are optional, and have sane defaults. They are:

    - **tree**: the source directory to build. Defaults to the current
      directory.
    - **output_dir**: directory where the build artifacts will be copied.
      Defaults to a new directory under `~/.cache/tuxmake/builds`.
    - **build_dir**: directory where the build will be performed. Defaults to
      a temporary directory under `output_dir`. An existing directory can be
      specified to do an incremental build on top of a previous one.
    - **target_arch**: target architecture name (`str`). Defaults to the native
      architecture of the hosts where tuxmake is running.
    - **toolchain**: toolchain to use in the build (`str`). Defaults to whatever Linux
      uses by default (`gcc`).
    - **wrapper**: compiler wrapper to use (`str`).
    - **environment**: environment variables to use in the build (`dict` with
      `str` as keys and values).
    - **kconfig**: which configuration to build (`str`). Defaults to
      `defconfig`.
    - **kconfig_add**: additional kconfig fragments/options to use. List of
      `str`, defaulting to an empty list.
    - **make_variables**: KEY=VALUE arguments to pass to `make`. `dict` with
      strings as values and strings as keys. Some `KEY`s are now allowed, as
      they would interfere with the tuxmake normal operation(e.g. `ARCH`, `CC`,
      `CROSS_COMPILE`, `HOSTCC`, INSTALL_MOD_PATH`, `INSTALL_DTBS_PATH`, `O`,
      etc).
    - **targets**: targets to build, list of `str`. If `None` or an empty list
      is passed, the default list of targets will be built.
    - **kernel_image**: which kernel image to build, overriding the default
      kernel image name defined for the target architecture.
    - **jobs**: number of concurrent jobs to run (as in `make -j N`). `int`,
      defaults to twice the number of available CPU cores.
    - **runtime:** name of the runtime to use (`str`).
    - **verbose**: do a verbose build. The default is to do a silent build
      (i.e.  `make -s`).
    - **quiet**: don't show the build logs in the console. The build log is
      still saved to the output directory, unconditionally.
    - **debug**: produce extra output for debugging tuxmake itself. This output
      will not appear in the build log.
    - **auto_cleanup**: whether to automatically remove the build directory
      after the build finishes. Ignored if *build_dir* is passed, in which
      case the build directory *will not be removed*.
    """

    MAKE_VARIABLES_REJECTLIST = [
        "ARCH",
        "CC",
        "CROSS_COMPILE",
        "HOSTCC",
        "INSTALL_DTBS_PATH",
        "INSTALL_MOD_PATH",
        "O",
    ]

    def __init__(
        self,
        tree=".",
        output_dir=None,
        build_dir=None,
        target_arch=None,
        toolchain=None,
        wrapper=None,
        environment={},
        kconfig=defaults.kconfig,
        kconfig_add=[],
        make_variables={},
        targets=defaults.targets,
        kernel_image=None,
        jobs=None,
        runtime=None,
        verbose=False,
        quiet=False,
        debug=False,
        auto_cleanup=True,
    ):
        self.source_tree = Path(tree).absolute()

        self.__output_dir__ = None
        self.__output_dir_input__ = output_dir
        self.__build_dir__ = None
        self.__build_dir_input__ = build_dir
        if self.__build_dir_input__:
            self.auto_cleanup = False
        else:
            self.auto_cleanup = auto_cleanup

        self.target_arch = target_arch and Architecture(target_arch) or host_arch
        self.toolchain = toolchain and Toolchain(toolchain) or NoExplicitToolchain()
        self.wrapper = wrapper and Wrapper(wrapper) or Wrapper("none")

        self.environment = environment

        self.kconfig = kconfig
        self.kconfig_add = kconfig_add

        for k in make_variables.keys():
            if k in self.MAKE_VARIABLES_REJECTLIST:
                raise UnsupportedMakeVariable(k)
        self.make_variables = make_variables

        if not targets:
            targets = defaults.targets

        if kernel_image:
            self.target_overrides = {"kernel": kernel_image}
        else:
            self.target_overrides = self.target_arch.targets

        self.targets = []
        self.__ordering_only_targets__ = {}
        for t in targets:
            self.add_target(t)
        self.cleanup_targets()

        if jobs:
            self.jobs = jobs
        else:
            self.jobs = defaults.jobs

        self.runtime = get_runtime(runtime)
        if not self.runtime.is_supported(self.target_arch, self.toolchain):
            raise UnsupportedArchitectureToolchainCombination(
                f"{self.target_arch}/{self.toolchain}"
            )

        self.verbose = verbose
        self.quiet = quiet
        self.debug = debug

        self.artifacts = {"log": ["build.log"]}
        self.__logger__ = None
        self.__status__ = {}
        self.__durations__ = {}
        self.metadata = OrderedDict()
        self.cmdline = CommandLine()

    @property
    def status(self):
        """
        A dictionary with target names (`str`) as keys, and `BuildInfo` objects
        as values.

        This property is only guaranteed to have a meaningful value after
        `run()` has been called.
        """
        return self.__status__

    def add_target(self, target_name, ordering_only=False):
        target = create_target(target_name, self)

        if ordering_only:
            if target_name not in self.__ordering_only_targets__:
                self.__ordering_only_targets__[target_name] = True
        else:
            self.__ordering_only_targets__[target_name] = False

        for d in target.dependencies:
            self.add_target(d, ordering_only=ordering_only)
        for a in target.runs_after:
            self.add_target(a, ordering_only=True)
        if target not in self.targets:
            self.targets.append(target)

    def cleanup_targets(self):
        self.targets = [
            t for t in self.targets if not self.__ordering_only_targets__[t.name]
        ]

    def validate(self):
        source = Path(self.source_tree)
        files = [str(f.name) for f in source.glob("*")]
        if "Makefile" in files and "Kconfig" in files and "Kbuild" in files:
            return
        raise UnrecognizedSourceTree(source.absolute())

    def prepare(self):
        self.log(
            "# to reproduce this build locally: "
            + quote_command_line(self.cmdline.reproduce(self))
        )
        self.runtime.prepare(self)
        self.wrapper.prepare(self)

    @property
    def output_dir(self):
        if self.__output_dir__:
            return self.__output_dir__

        if self.__output_dir_input__ is None:
            self.__output_dir__ = get_new_output_dir()
        else:
            self.__output_dir__ = Path(self.__output_dir_input__)
            self.__output_dir__.mkdir(exist_ok=True)
        return self.__output_dir__

    @property
    def build_dir(self):
        if self.__build_dir__:
            return self.__build_dir__

        if self.__build_dir_input__:
            self.__build_dir__ = Path(self.__build_dir_input__)
            self.__build_dir__.mkdir(parents=True, exist_ok=True)
        else:
            self.__build_dir__ = self.output_dir / "tmp"
            self.__build_dir__.mkdir()
        return self.__build_dir__

    def get_silent(self):
        if self.verbose:
            return []
        else:
            return ["--silent"]

    def run_cmd(self, origcmd, stdout=None, interactive=False):
        """
        Performs the build.

        After the build is finished, the results can be inspected via
        `status`, `passed`, and `failed`.
        """
        cmd = []
        for c in origcmd:
            cmd += self.expand_cmd_part(c)

        if cmd[0] == "!":
            expect_failure = True
            cmd.pop(0)
        else:
            expect_failure = False

        final_cmd = self.runtime.get_command_line(self, cmd, interactive)
        extra_env = dict(**self.wrapper.environment, **self.environment, LANG="C.UTF-8")
        env = dict(os.environ, **extra_env)

        logger = self.logger.stdin
        if interactive:
            stdout = stderr = stdin = None
        else:
            stdin = subprocess.DEVNULL
            stderr = logger
            if not stdout:
                self.log(quote_command_line(cmd))
                stdout = logger

        self.log_debug(f"Command: {final_cmd}")
        if extra_env:
            self.log_debug(f"Environment: {extra_env}")
        try:
            with self.measure_duration("Command"):
                process = subprocess.Popen(
                    final_cmd,
                    cwd=self.source_tree,
                    env=env,
                    stdin=stdin,
                    stdout=stdout,
                    stderr=stderr,
                )
            process.communicate()
            if expect_failure:
                return process.returncode != 0
            else:
                return process.returncode == 0
        except KeyboardInterrupt:
            process.terminate()
            sys.exit(1)

    @contextmanager
    def measure_duration(self, name, metadata=None):
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            if metadata:
                self.__durations__[metadata] = duration
            self.log_debug(f"{name} finished in {duration} seconds.")

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
            source_tree=self.source_tree,
            build_dir=self.build_dir,
            target_arch=self.target_arch.name,
            toolchain=self.toolchain.name,
            wrapper=self.wrapper.name,
            kconfig=self.kconfig,
            **self.target_overrides,
        )

    @property
    def logger(self):
        if not self.__logger__:
            if self.quiet:
                stdout = subprocess.DEVNULL
            else:
                stdout = sys.stdout
            self.__logger__ = subprocess.Popen(
                ["tee", str(self.output_dir / "build.log")],
                stdin=subprocess.PIPE,
                stdout=stdout,
            )
        return self.__logger__

    def log(self, *stuff):
        subprocess.call(["echo"] + list(stuff), stdout=self.logger.stdin)

    def log_debug(self, *stuff):
        if self.debug:
            print("D:", *stuff, file=sys.stderr)

    @property
    def make_args(self):
        return [f"{k}={v}" for k, v in self.makevars.items() if v]

    @property
    def makevars(self):
        mvars = {}
        mvars.update(self.make_variables)
        mvars.update(self.target_arch.makevars)
        mvars.update(self.toolchain.expand_makevars(self.target_arch))
        mvars.update(self.wrapper.wrap(mvars))
        return mvars

    def build_all_targets(self):
        for target in self.targets:
            start = time.time()
            result = self.build(target)
            result.duration = time.time() - start
            self.status[target.name] = result

    def build(self, target):
        for dep in target.dependencies:
            if not self.status[dep].passed:
                self.log_debug(
                    f"Skipping {target.name} because dependency {dep} failed"
                )
                return BuildInfo("SKIP")

        for precondition in target.preconditions:
            if not self.run_cmd(precondition, stdout=subprocess.DEVNULL):
                self.log_debug(f"Skipping {target.name} because precondition failed")
                return BuildInfo("SKIP")

        target.prepare()

        fail = False
        for cmd in target.commands:
            if not self.run_cmd(cmd):
                fail = True
                break

        if not fail and not self.check_artifacts(target):
            fail = True

        if fail:
            return BuildInfo("FAIL")

        return BuildInfo("PASS")

    def check_artifacts(self, target):
        ret = True
        for _, f in target.artifacts.items():
            artifact = self.build_dir / f
            if not artifact.exists():
                self.log(f"E: expected artifact {f} does not exist!")
                ret = False
        return ret

    def copy_artifacts(self, target):
        if not self.status[target.name].passed:
            return
        self.artifacts[target.name] = []
        for origdest, origsrc in target.artifacts.items():
            dest = self.output_dir / origdest
            src = self.build_dir / origsrc
            shutil.copy(src, Path(self.output_dir / dest))
            self.artifacts[target.name].append(origdest)

    @property
    def passed(self):
        """
        `False` if any targets failed, `True` otherwise.

        This property is only guaranteed to have a meaningful value after
        `run()` has been called.
        """
        return not self.failed

    @property
    def failed(self):
        """
        `True` if any target failed to build, `False` otherwise.

        This property is only guaranteed to have a meaningful value after
        `run()` has been called.
        """
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
            "reproducer_cmdline": self.cmdline.reproduce(self),
        }
        errors, warnings = self.parse_log()
        self.metadata["results"] = {
            "status": "PASS" if self.passed else "FAIL",
            "targets": {
                name: {"status": s.status, "duration": s.duration}
                for name, s in self.status.items()
            },
            "artifacts": self.artifacts,
            "errors": errors,
            "warnings": warnings,
            "duration": self.__durations__,
        }
        self.metadata["tuxmake"] = {"version": __version__}

        extractor = MetadataExtractor(self)
        self.metadata.update(extractor.extract())

    def save_metadata(self):
        with (self.output_dir / "metadata.json").open("w") as f:
            f.write(json.dumps(self.metadata, indent=4, sort_keys=True))
            f.write("\n")

    def parse_log(self):
        parser = LogParser()
        parser.parse(self.output_dir / "build.log")
        return parser.errors, parser.warnings

    def terminate(self):
        self.logger.terminate()

    def cleanup(self):
        shutil.rmtree(self.build_dir, ignore_errors=True)

    def run(self):
        """
        Performs the build. After this method completes, the results of the
        build can be inspected though the `status`, `passed`, and `failed`
        properties.
        """
        with self.measure_duration("Input validation", metadata="validate"):
            self.validate()

        with self.measure_duration("Preparation", metadata="prepare"):
            self.prepare()

        with self.measure_duration("Build", metadata="build"):
            self.build_all_targets()

        with self.measure_duration("Copying Artifacts", metadata="copy"):
            for target in self.targets:
                self.copy_artifacts(target)

        with self.measure_duration("Metadata Extraction", metadata="metadata"):
            self.extract_metadata()

        with self.measure_duration("Cleanup", metadata="cleanup"):
            self.terminate()
            if self.auto_cleanup:
                self.cleanup()

        self.save_metadata()


def build(**kwargs):
    """
    This function instantiates a `Build` objecty, forwarding all the options
    received in `**kwargs`. It hen calls `run()` on that instance, and returns
    it. It can be used as quick way of running a build and inspecting the
    results.

    For full control over the build, you will probably want to use the `Build`
    class directly.
    """
    builder = Build(**kwargs)
    builder.run()
    return builder
