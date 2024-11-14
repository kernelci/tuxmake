from contextlib import contextmanager
from concurrent import futures
from collections import OrderedDict
from pathlib import Path
import json
import os
import signal
import shutil
import subprocess
import tempfile
import time
from tuxmake import __version__
from tuxmake import deprecated
from tuxmake.logging import set_debug, debug
from tuxmake.arch import Architecture, native_arch
from tuxmake.toolchain import Toolchain, NoExplicitToolchain
from tuxmake.wrapper import Wrapper
from tuxmake.output import get_new_output_dir, get_default_korg_toolchains_dir
from tuxmake.target import Compression
from tuxmake.target import default_compression
from tuxmake.target import create_target
from tuxmake.runtime import Runtime, DockerRuntime
from tuxmake.runtime import Terminated
from tuxmake.metadata import MetadataCollector
from tuxmake.exceptions import EnvironmentCheckFailed
from tuxmake.exceptions import KorgGccPreparationFailed
from tuxmake.exceptions import KorgGccDownloadAllToolchainFailed
from tuxmake.exceptions import UnrecognizedSourceTree
from tuxmake.exceptions import UnsupportedArchitectureToolchainCombination
from tuxmake.exceptions import UnsupportedMakeVariable
from tuxmake.log import LogParser
from tuxmake.cmdline import CommandLine
from tuxmake.build_utils import defaults
from tuxmake.utils import quote_command_line
from tuxmake.utils import get_directory_timestamp


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
    - **korg_toolchains_dir**: directory where the kernel.org toolchain
      tarballs will be cached. Defaults to `~/.cache/tuxmake/korg_toolchains`.
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
      `HOSTCC`, INSTALL_MOD_PATH`, `INSTALL_DTBS_PATH`, `O`,  etc).
    - **targets**: targets to build, list of `str`. If `None` or an empty list
      is passed, the default list of targets will be built.
    - **compression_type**: compression type to use in compressed artifacts.
      `str`, must be one of "xz", "none".
    - **kernel_image**: which kernel image to build, overriding the default
      kernel image name defined for the target architecture.
    - **jobs**: number of concurrent jobs to run (as in `make -j N`). `int`,
      defaults to the number of available CPU cores.
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
        korg_toolchains_dir=None,
        target_arch=None,
        toolchain=None,
        wrapper=None,
        environment=None,
        kconfig=defaults.kconfig,
        kconfig_add=None,
        make_variables=None,
        targets=defaults.targets,
        compression_type=None,
        kernel_image=None,
        jobs=None,
        runtime=None,
        fail_fast=False,
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
        self.__korg_toolchains_dir__ = None
        self.__korg_toolchains_dir_input__ = korg_toolchains_dir
        if self.__build_dir_input__:
            self.clean_build_tree = False
        else:
            self.clean_build_tree = True
        self.auto_cleanup = auto_cleanup

        self.target_arch = target_arch and Architecture(target_arch) or native_arch
        self.toolchain = toolchain and Toolchain(toolchain) or NoExplicitToolchain()
        self.prepare_korg_gcc = False
        self.korg_gcc_cross_prefix = None
        if self.toolchain.name.startswith("korg-gcc"):
            self.prepare_korg_gcc = True

        self.wrapper = wrapper and Wrapper(wrapper) or Wrapper("none")

        self.timestamp = get_directory_timestamp(self.source_tree)
        self.__environment__ = None
        self.__environment_input__ = environment or {}

        self.kconfig = kconfig
        self.kconfig_add = kconfig_add or []

        self.make_variables = make_variables or {}
        for k in self.make_variables.keys():
            if k in self.MAKE_VARIABLES_REJECTLIST:
                raise UnsupportedMakeVariable(k)

        self.dynamic_make_variables = dict(self.target_arch.dynamic_makevars)

        if not targets:
            targets = defaults.targets

        if kernel_image:
            self.target_overrides = {"kernel": kernel_image}
        else:
            self.target_overrides = self.target_arch.targets

        if compression_type:
            self.compression = Compression(compression_type)
        else:
            self.compression = default_compression
        self.targets = []
        self.__ordering_only_targets__ = {}
        for t in targets:
            self.add_target(t)
        self.cleanup_targets()
        self.extend_kconfig()

        if jobs:
            self.jobs = jobs
        else:
            self.jobs = defaults.jobs

        self.runtime = Runtime.get(runtime)
        self.runtime.set_image(get_image(self))

        if not self.runtime.is_supported(self.target_arch, self.toolchain):
            raise UnsupportedArchitectureToolchainCombination(
                f"{self.target_arch}/{self.toolchain}"
            )

        self.fail_fast = fail_fast
        self.interrupted = False
        if self.fail_fast:
            self.keep_going = []
        else:
            self.keep_going = ["--keep-going"]
        self.verbose = verbose
        self.quiet = quiet
        self.debug = debug
        set_debug(self.debug)

        self.offline = False

        self.artifacts = {"log": ["build.log", "build-debug.log"]}
        self.__status__ = {}
        self.__durations__ = {}
        self.metadata_collector = MetadataCollector(self)
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
        target = create_target(target_name, self, self.compression)

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

    def extend_kconfig(self):
        for target in self.targets:
            self.kconfig_add.extend(target.kconfig_add)

    def validate(self):
        source = Path(self.source_tree)
        files = [str(f.name) for f in source.glob("*")]
        if "Makefile" in files and "Kconfig" in files and "Kbuild" in files:
            return
        raise UnrecognizedSourceTree(source.absolute())

    def prepare(self):
        self.wrapper.prepare_host()

        self.runtime.basename = "build"
        self.runtime.quiet = self.quiet
        self.runtime.source_dir = self.source_tree
        self.runtime.output_dir = self.output_dir
        self.runtime.add_volume(self.build_dir)
        if self.prepare_korg_gcc:
            self.runtime.add_volume(self.korg_toolchains_dir)
        if self.wrapper.path:
            self.runtime.add_volume(
                str(self.wrapper.path), f"/usr/local/bin/{self.wrapper.name}"
            )
        wenv = self.wrapper.environment
        env = dict(**wenv, **self.environment, LANG="C")
        self.runtime.environment = env
        for k, v in wenv.items():
            if k.endswith("_DIR"):
                self.runtime.add_volume(v)
        self.runtime.prepare()
        self.wrapper.prepare_runtime(self)

        if self.toolchain.version_suffix and self.runtime.name == "null":
            toolchain = self.toolchain
            compiler = toolchain.compiler(self.target_arch)
            self.log(
                f"W: Requested {toolchain}, but versioned toolchains are not supported by the null runtime. Will use whatever version of {compiler} that you have installed. To ensure {toolchain} is used, try use a container-based runtime instead."
            )

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
            self.__build_dir__ = self.output_dir / "build"
            self.__build_dir__.mkdir()
        return self.__build_dir__

    @property
    def korg_toolchains_dir(self):
        if self.__korg_toolchains_dir__:
            return self.__korg_toolchains_dir__

        if self.__korg_toolchains_dir_input__ is None:
            self.__korg_toolchains_dir__ = get_default_korg_toolchains_dir()
        else:
            self.__korg_toolchains_dir__ = Path(self.__korg_toolchains_dir_input__)
        self.__korg_toolchains_dir__.mkdir(parents=True, exist_ok=True)
        return self.__korg_toolchains_dir__

    @property
    def environment(self):
        if self.__environment__ is not None:
            return self.__environment__
        env = {}
        env["KBUILD_BUILD_TIMESTAMP"] = "@" + self.timestamp
        env["KBUILD_BUILD_USER"] = "tuxmake"
        env["KBUILD_BUILD_HOST"] = "tuxmake"
        env["KCFLAGS"] = f"-ffile-prefix-map={self.build_dir}/="
        env.update(self.__environment_input__)
        self.__environment__ = env
        return self.__environment__

    def get_silent(self):
        if self.verbose:
            return []
        else:
            return ["--silent"]

    @contextmanager
    def go_offline(self):
        self.offline = True
        try:
            yield
        finally:
            self.offline = False

    def run_cmd(self, origcmd, stdout=None, interactive=False, echo=True, makevars={}):
        """
        Performs the build.

        After the build is finished, the results can be inspected via
        `status`, `passed`, and `failed`.
        """
        cmd = []
        for c in origcmd:
            cmd += self.expand_cmd_part(c, makevars)

        if cmd[0] == "!":
            expect_failure = True
            cmd.pop(0)
        else:
            expect_failure = False

        try:
            with self.measure_duration("Command"):
                return self.runtime.run_cmd(
                    cmd,
                    interactive=interactive,
                    echo=echo,
                    stdout=stdout,
                    expect_failure=expect_failure,
                    offline=self.offline,
                )
        except (KeyboardInterrupt, Terminated) as ex:
            self.log(str(ex))
            self.interrupted = True
            return False

    @contextmanager
    def measure_duration(self, name, metadata=None):
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            if metadata:
                self.__durations__[metadata] = duration
            debug(f"{name} finished in {duration} seconds.")

    def expand_cmd_part(self, part, makevars):
        if part == "{make}":
            return (
                ["make"]
                + self.get_silent()
                + self.keep_going
                + [f"--jobs={self.jobs}", f"O={self.build_dir}"]
                + self.make_args(makevars)
            )
        elif part == "{tar_caf}":
            return [
                "tar",
                "--sort=name",
                "--owner=tuxmake:1000",
                "--group=tuxmake:1000",
                "--mtime=@" + self.timestamp,
                "--clamp-mtime",
                "-caf",
            ]
        elif part == "{z}":
            return self.compression.command
        else:
            return [self.format_cmd_part(part)]

    def format_cmd_part(self, part):
        return part.format(
            source_tree=self.source_tree,
            build_dir=self.build_dir,
            source_arch=self.target_arch.source_arch,
            toolchain=self.toolchain.name,
            wrapper=self.wrapper.name,
            kconfig=self.kconfig,
            z_ext=self.compression.extension,
            **self.target_overrides,
        )

    def log(self, *stuff):
        self.runtime.log(*stuff)

    def make_args(self, makevars):
        # we want to override target makevars with user provided make_variables
        expanded_makevars = {k: self.format_cmd_part(v) for k, v in makevars.items()}
        expanded_makevars.update(self.makevars)
        return [f"{k}={v}" for k, v in expanded_makevars.items() if v]

    @property
    def makevars(self):
        mvars = {}
        mvars.update(self.target_arch.makevars)
        mvars.update(self.toolchain.expand_makevars(self.target_arch))
        if self.korg_gcc_cross_prefix:
            mvars["CROSS_COMPILE"] = self.korg_gcc_cross_prefix
        mvars.update(self.make_variables)
        mvars.update(self.wrapper.wrap(mvars))
        return mvars

    def get_dynamic_makevars(self):
        for k, v in self.dynamic_make_variables.items():
            if k not in self.make_variables:
                self.make_variables[k] = self.get_command_output(v).strip()

    def get_command_output(self, cmd):
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as f:
            self.run_cmd(["sh", "-c", cmd], stdout=f, echo=False)
            f.seek(0)
            return f.read().strip()

    def build_all_targets(self):
        skip_all = False
        self.get_dynamic_makevars()
        for target in self.targets:
            start = time.time()
            if skip_all:
                result = BuildInfo("SKIP")
            else:
                result = self.build(target)
                if (self.fail_fast and result.failed) or self.interrupted:
                    skip_all = True
            result.duration = time.time() - start
            self.status[target.name] = result

    def build(self, target):
        for dep in target.dependencies:
            if not self.status[dep].passed:
                debug(f"Skipping {target.name} because dependency {dep} failed")
                return BuildInfo("SKIP")

        for precondition in target.preconditions:
            if not self.run_cmd(precondition, echo=False, stdout=subprocess.DEVNULL):
                debug(f"Skipping {target.name} because precondition failed")
                return BuildInfo("SKIP")

        target.prepare()

        fail = False
        for cmd in target.commands:
            if not self.run_cmd(
                cmd, makevars=target.makevars, interactive=cmd.interactive
            ):
                fail = True
                break

        if not fail and not self.check_artifacts(target):
            fail = True

        if fail:
            return BuildInfo("FAIL")

        return BuildInfo("PASS")

    def check_artifacts(self, target):
        ret = True
        for _, artifact in target.find_artifacts(self.build_dir):
            if not artifact.exists():
                self.log(f"E: expected artifact {artifact} does not exist!")
                ret = False
        return ret

    def copy_artifacts(self, target):
        self.artifacts[target.name] = []
        for origdest, src in target.find_artifacts(self.build_dir):
            if not src.exists():
                continue
            dest = self.output_dir / origdest
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

    def collect_metadata(self):
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
        self.metadata["runtime"] = self.runtime.get_metadata()

        extracted = self.metadata_collector.collect()
        self.metadata.update(extracted)

    def save_metadata(self):
        with (self.output_dir / "metadata.json").open("w") as f:
            f.write(json.dumps(self.metadata, indent=4, sort_keys=True))
            f.write("\n")

    def parse_log(self):
        parser = LogParser()
        parser.parse(self.output_dir / "build.log")
        return parser.errors, parser.warnings

    def cleanup(self):
        self.runtime.cleanup()
        if self.clean_build_tree:
            shutil.rmtree(self.build_dir, ignore_errors=True)

    def check_environment(self):
        self.runtime.prepare()
        self.get_dynamic_makevars()
        cmd = [str(self.runtime.get_check_environment_command())]
        cmd.append(f"{self.target_arch.name}_{self.toolchain.name}")
        makevars = self.makevars
        cross = makevars.get("CROSS_COMPILE")
        if cross:
            cmd.append(cross)
        if "CROSS_COMPILE_COMPAT" in self.dynamic_make_variables:
            cross_compat = makevars.get("CROSS_COMPILE_COMPAT")
            if cross_compat:
                cmd.append(cross_compat)
            else:
                cmd.append("")
        result = self.run_cmd(cmd)
        self.cleanup()
        if not result:
            raise EnvironmentCheckFailed()

    def prepare_korg_gcc_toolchain(self):
        suffix = self.toolchain.suffix()
        tc_full_version = self.runtime.get_toolchain_full_version(self.toolchain.name)
        # TODO: Find a better way to avoid the following conditional checks
        target_arch = self.target_arch.name
        if self.target_arch.name == "arm":
            suffix = f"{suffix}-gnueabi"
        elif self.target_arch.name == "arm64":
            target_arch = "aarch64"
        elif self.target_arch.name == "openrisc":
            target_arch = "or1k"
        elif self.target_arch.name.startswith("parisc"):
            target_arch = "hppa"
        else:
            target_arch = self.target_arch.name

        # Calculate the cross compile tool prefix
        # TODO: Consider adding cross tools to the PATH and simplifying this
        self.korg_gcc_cross_prefix = f"{str(self.build_dir)}/gcc-{tc_full_version}-nolibc/{target_arch}-{suffix}/bin/{target_arch}-{suffix}-"

        # Run the korg gcc script to download the toolchain archive if required
        cmd = [str(self.runtime.get_prepare_korg_gcc_command())]
        cmd.append(native_arch.name)
        cmd.append(self.runtime.get_toolchain_full_version(self.toolchain.name))
        cmd.append(target_arch)
        cmd.append(suffix)
        cmd.append(str(self.korg_toolchains_dir))
        cmd.append(str(self.build_dir))
        result = self.run_cmd(cmd)
        if not result:
            raise KorgGccPreparationFailed()

    def _download_all_korg_gcc_toolchains(self, version):
        cmd = [str(self.runtime.get_download_all_korg_gcc_command())]
        cmd.append(str(self.korg_toolchains_dir))
        cmd.append(native_arch.name)
        cmd.append(version)
        result = self.run_cmd(cmd)
        if not result:
            raise KorgGccDownloadAllToolchainFailed()

    def download_all_korg_gcc_toolchains(self):
        self.runtime.prepare()
        versions = []
        runtime = DockerRuntime()
        for tc in runtime.toolchains:
            if tc.startswith("korg-gcc-"):
                versions.append(runtime.get_toolchain_full_version(tc))
        with futures.ThreadPoolExecutor() as executor:
            thread_count = 0
            for __ in executor.map(self._download_all_korg_gcc_toolchains, versions):
                if len(versions) > 0:
                    thread_count += 1
                    print(
                        f"Processed: {round((thread_count/len(versions))*100)}%",
                        end="\r",
                        flush=True,
                    )
        count = len(os.listdir(str(self.korg_toolchains_dir)))
        self.log(f"\nDownloaded {count} kernel.org gcc toolchain archives.")

    def run(self):
        """
        Performs the build. After this method completes, the results of the
        build can be inspected though the `status`, `passed`, and `failed`
        properties.
        """
        old_sigterm = signal.signal(signal.SIGTERM, Terminated.handle_signal)

        prepared = False
        try:
            self.metadata_collector.before_build()

            with self.measure_duration("Input validation", metadata="validate"):
                self.validate()

            with self.measure_duration("Preparation", metadata="prepare"):
                self.prepare()
                if self.prepare_korg_gcc:
                    self.prepare_korg_gcc_toolchain()

            prepared = True
            self.log(quote_command_line(self.cmdline.reproduce(self)))

            with self.go_offline():
                with self.measure_duration("Build", metadata="build"):
                    self.build_all_targets()
        finally:
            with self.measure_duration("Copying Artifacts", metadata="copy"):
                for target in self.targets:
                    self.copy_artifacts(target)

            with self.measure_duration("Metadata Extraction", metadata="metadata"):
                if prepared:
                    self.collect_metadata()

            with self.measure_duration("Cleanup", metadata="cleanup"):
                if self.auto_cleanup:
                    self.cleanup()

            self.save_metadata()

            signal.signal(signal.SIGTERM, old_sigterm)


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


DEFAULT_CONTAINER_REGISTRY = "docker.io"


def get_image(build):
    image = (
        os.getenv("TUXMAKE_IMAGE")
        or deprecated.getenv("TUXMAKE_DOCKER_IMAGE", "TUXMAKE_IMAGE")
        or build.target_arch.get_image(build.toolchain)
        or build.toolchain.get_image(build.target_arch)
    )
    registry = os.getenv("TUXMAKE_IMAGE_REGISTRY", DEFAULT_CONTAINER_REGISTRY)
    if registry:
        parts = image.split("/")
        localhost = parts[0] == "localhost"
        remotehost = len(parts[0].split(".")) > 1
        if len(parts) < 3 and not localhost and not remotehost:
            # only prepend registry if the image name is not already a full
            # image name.
            image = registry + "/" + image
    tag = os.getenv("TUXMAKE_IMAGE_TAG")
    if tag:
        image = image + ":" + tag
    return image
