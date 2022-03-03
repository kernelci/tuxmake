import os
import re
import shlex
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Optional, TextIO


from tuxmake import cache
from tuxmake.logging import debug, warning
from tuxmake.config import ConfigurableObject, split, splitmap, splitlistmap
from tuxmake.exceptions import RuntimePreparationFailed
from tuxmake.exceptions import ImageRequired
from tuxmake.exceptions import InvalidRuntimeError
from tuxmake.toolchain import Toolchain
from tuxmake.arch import host_arch
from tuxmake.utils import quote_command_line


DEFAULT_RUNTIME = "null"
DEFAULT_CONTAINER_REGISTRY = "docker.io"


class Terminated(Exception):
    """
    This is an exception class raised by `Runtime.run_cmd` in the case the
    currently running command gets terminated (via `kill`, or by the user
    typing control-C).
    """

    def __init__(self, msg):
        super().__init__(msg)

    @staticmethod
    def handle_signal(signum, _):
        raise Terminated(f"received signal {signum}; terminating ...")


class Runtime(ConfigurableObject):
    """
    This class encapsulates running commands against the local host system or a
    container, in a way that is transparent to the caller.

    You should usually not need to instantiate this class directly. Instead,
    you can get objects of this class by calling `Runtime.get()` (see below).


    After obtaining a runtime objects, you might set the following attributes
    on it to control its behavior:

    * **basename**: base name to use when creating file (e.g. log files). Files
      will be named "{basename}.log" and "{basename}-debug.log". Type: `str`;
      defaults to `"run"`.
    * **quiet**: whether to run a quietly or not. Type: `bool`; defaults to `False`.
    * **source_dir**: directory where commands are run. For container runtimes,
      this directory is bind mounted inside the container under the same
      location.
      Type: `Path`; defaults to the current working directory.
    * **output_dir**: directory where to save logs of the execution.
      For container runtimes, this directory is bind mounted inside the
      container under the same location.
      Type: `Optional[Path]`; defaults to `None` (meaning, no logs are saved).
    * **environment**: extra environment variables to be used for all commands
      ran by this runtime. Type: `dict` with `str` keys and values; defaults to
      an empty dict.
    """

    basedir = "runtime"
    name = "runtime"
    exception = InvalidRuntimeError
    bindir = Path(__file__).parent / basedir / "bin"

    @staticmethod
    def get(name):
        """
        Creates and returns a new `Runtime` object.The returned objects will be
        of a subclass of `Runtime`, depending on the **name** argument. Supported runtimes are:

        * `null`: runs commands on the host system.
        * `docker`: runs commands on a Docker container. All commands ran by
          the same runtime instance are executed in the same container (i.e.
          state between calls is persisted).
        * `docker-local`: the same as `docker`, but will only use local images
          (i.e. it will never pull remote images).
        * `podman`: run commands on a Podman container.
        * `podman-local`: like `docker-local`, but with Podman.
        """
        name = name or DEFAULT_RUNTIME
        name = "".join([w.title() for w in re.split(r"[_-]", name)]) + "Runtime"
        try:
            here = sys.modules[__name__]
            cls = getattr(here, name)
            return cls()
        except AttributeError:
            raise InvalidRuntimeError(name)

    def __init__(self):
        super().__init__(self.name)
        self.__offline_available__ = None
        self.__image__ = None
        self.__logger__: Optional[subprocess.Popen] = None

        self.basename: str = "run"
        self.quiet: bool = False
        self.source_dir: Path = Path.cwd()
        self.output_dir: Optional[Path] = None
        self.environment = {}

    def __init_config__(self):
        self.toolchains = Toolchain.supported()

    def get_image(self):
        if not self.__image__:
            raise ImageRequired()
        return self.__image__

    def set_image(self, image):
        """
        Sets the container image to use. This has no effect on non-container
        runtimes.
        """
        self.__image__ = image

    def is_supported(self, arch, toolchain):
        return True

    @property
    def offline_available(self):
        if self.__offline_available__ is None:
            prefix = self.get_command_prefix(False)
            go_offline = str(self.get_go_offline_command())
            try:
                subprocess.check_output(
                    [*prefix, go_offline, "true"], stderr=subprocess.STDOUT
                )
                self.__offline_available__ = True
            except subprocess.CalledProcessError as exc:
                error = exc.output.decode("utf-8").strip()
                warning(f"Support for running offline not available ({error})")
                self.__offline_available__ = False
        return self.__offline_available__

    def get_command_line(self, cmd, interactive, offline=True):
        prefix = self.get_command_prefix(interactive)
        if offline and self.offline_available:
            go_offline = [str(self.get_go_offline_command())]
        else:
            go_offline = []
        return [*prefix, *go_offline, *cmd]

    def get_command_prefix(self, interactive):
        return []

    def add_volume(self, source, dest=None):
        """
        Ensures that the directory or file **source** is available for commands
        run as **dest**. For container runtimes, this meand bind-mounting
        **source** as **dest** inside the container. All volumes must be added
        before `prepare()` is called.

        This is a noop for non-container runtimes.
        """
        pass

    def prepare(self):
        """
        Initializes the runtime object. Must be called before actually running
        any commands with `run_cmd`.
        """
        pass

    def get_go_offline_command(self):
        return self.bindir / "tuxmake-run-offline"

    def get_check_environment_command(self):
        return self.bindir / "tuxmake-check-environment"

    def get_metadata(self):
        """
        Extracts metadata about the runtime (e.g. docker version, image name
        and sha256sum, etc).
        """
        return {}

    @property
    def logger(self):
        if not self.__logger__:
            if self.quiet:
                stdout = subprocess.DEVNULL
            else:
                stdout = sys.stdout
            if self.output_dir:
                log = self.output_dir / f"{self.basename}.log"
                debug_log = self.output_dir / f"{self.basename}-debug.log"
            else:
                log = debug_log = Path("/dev/null")
            self.__logger__ = subprocess.Popen(
                [
                    str(Runtime.bindir / "tuxmake-logger"),
                    str(log),
                    str(debug_log),
                ],
                stdin=subprocess.PIPE,
                stdout=stdout,
            )
        return self.__logger__

    def log(self, *stuff):
        """
        Logs **stuff** to both the console and to any log files in use.
        """
        subprocess.call(["echo"] + list(stuff), stdout=self.logger.stdin)

    def cleanup(self):
        """
        Cleans up and returns resources used during execution. You must call
        this methods after you are done with the runtime object.
        """
        self.logger.communicate()
        self.logger.terminate()

    def run_cmd(
        self,
        cmd,
        interactive: bool = False,
        offline: bool = True,
        expect_failure: bool = False,
        stdout: Optional[TextIO] = None,
        echo: bool = True,
    ):
        """
        Runs a command in the desired runtime. Returns True if the command
        succeeds (i.e. exits with a status code of 0); False otherwise.
        Parameters:

        * **cmd**: The command to run. must be a list of strings (like with the
          `subprocess` functions, e.g. check_call).
        * **interactive**: whether this commands needs user interaction.
        * **offline**: whether this commands should run offline, i.e. with no
          access to non-loopback network interfaces.
        * **expect_failure**: whether a failure, i.e. a non-zero return status,
          is to be expected. Reverses the logic of the return value of this
          method, i.e. returns True if the command fails, False if it succeeds.
        * **stdout**: a TextIO object to where the `stdout` of the called
          command will be directed.

        If the command in interrupted in some way (by a TERM signal, or by the
        user typing control-C), an instance of `Terminated` is raised.
        """
        final_cmd = self.get_command_line(cmd, interactive=interactive, offline=offline)

        if interactive:
            stdout = stderr = stdin = None
        else:
            stdin = subprocess.DEVNULL
            stderr = self.logger.stdin
            if not stdout:
                stdout = self.logger.stdin
        if echo:
            self.log(quote_command_line(cmd))

        env = dict(**os.environ)
        env.update(self.environment)

        debug(f"Command: {final_cmd}")
        if self.environment:
            debug(f"Environment: {self.environment}")
        process = subprocess.Popen(
            final_cmd,
            cwd=self.source_dir,
            env=env,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )
        try:
            process.communicate()
            if expect_failure:
                return process.returncode != 0
            else:
                return process.returncode == 0
        finally:
            process.terminate()


class NullRuntime(Runtime):
    name = "null"


class Image:
    def __init__(
        self,
        name,
        kind,
        base,
        hosts,
        rebuild,
        group=None,
        targets="",
        skip_build=False,
        target_bases="",
        target_kinds="",
        target_hosts="",
        target_skip="",
        packages="",
        install_options="",
        extra_apt_repo=None,
        extra_apt_repo_key=None,
    ):
        self.name = name
        self.kind = kind
        self.base = base
        self.hosts = split(hosts)
        self.group = group
        self.targets = split(targets)
        self.skip_build = skip_build
        self.target_bases = splitmap(target_bases)
        self.target_kinds = splitmap(target_kinds)
        self.target_hosts = splitlistmap(target_hosts)
        self.target_skip = split(target_skip)
        self.packages = split(packages)
        self.install_options = install_options
        self.rebuild = rebuild
        self.extra_apt_repo = extra_apt_repo
        self.extra_apt_repo_key = extra_apt_repo_key


class ContainerRuntime(Runtime):
    prepare_failed_msg = "failed to pull remote image {image}"
    bindir = Path("/tuxmake")

    def __init_config__(self):
        self.base_images = []
        self.ci_images = []
        self.toolchain_images = []
        self.toolchains = split(self.config["runtime"]["toolchains"])
        for image_list, config in (
            (self.base_images, self.config["runtime"]["bases"]),
            (self.toolchain_images, self.toolchains),
        ):
            for entry in split(config):
                if entry not in self.config:
                    continue
                if entry.startswith("base"):
                    group = "base"
                else:
                    group = f"{entry}_all"
                image = Image(name=entry, group=group, **self.config[entry])
                image_list.append(image)
                for target in image.targets:
                    cross_config = dict(self.config[entry])
                    cross_config["base"] = image.target_bases.get(target, image.name)
                    cross_config["kind"] = image.target_kinds.get(
                        target, "cross-" + image.kind
                    )
                    cross_config["hosts"] = image.target_hosts.get(target, image.hosts)
                    cross_config["skip_build"] = target in image.target_skip
                    cross_image = Image(
                        name=f"{target}_{image.name}", group=group, **cross_config
                    )
                    image_list.append(cross_image)
        self.images = self.base_images + self.ci_images + self.toolchain_images
        self.toolchain_images_map = {
            f"tuxmake/{image.name}": image for image in self.toolchain_images
        }
        self.container_id = None

    __volumes__ = None

    @property
    def volumes(self):
        if self.__volumes__ is None:
            self.__volumes__ = []
        return self.__volumes__

    def add_volume(self, source, dest=None):
        self.volumes.append((source, dest or source))

    @lru_cache(None)
    def is_supported(self, arch, toolchain):
        image_name = arch.get_image(toolchain) or toolchain.get_image(arch)
        image = self.toolchain_images_map.get(image_name)
        if image:
            return host_arch.name in image.hosts or any(
                [a in image.hosts for a in host_arch.aliases]
            )
        else:
            return False

    def prepare(self):
        super().prepare()
        try:
            self.prepare_image()
            self.start_container()
        except subprocess.CalledProcessError:
            raise RuntimePreparationFailed(
                self.prepare_failed_msg.format(image=self.get_image())
            )

    def prepare_image(self):
        pull = [self.command, "pull", self.get_image()]
        last_pull = cache.get(pull)
        now = time.time()
        if last_pull:
            a_day_ago = now - (24 * 60 * 60)
            if last_pull > a_day_ago:
                return
        subprocess.check_call(pull)
        cache.set(pull, time.time())

    def start_container(self):
        env = (f"--env={k}={v}" for k, v in self.environment.items())

        user_opts = self.get_user_opts()
        extra_opts = self.__get_extra_opts__()
        cmd = [
            self.command,
            "run",
            "--rm",
            "--init",
            "--detach",
            "--env=KBUILD_BUILD_USER=tuxmake",
            *env,
            *user_opts,
            *self.get_volume_opts(),
            f"--workdir={self.source_dir}",
            *self.get_logging_opts(),
            *extra_opts,
            self.get_image(),
            "sleep",
            "1d",
        ]
        debug(f"Starting container: {cmd}")
        self.container_id = self.spawn_container(cmd)
        debug(f"Container ID: {self.container_id}")

    def spawn_container(self, cmd):
        return subprocess.check_output(cmd).strip().decode("utf-8")

    def get_command_prefix(self, interactive):
        if interactive:
            interactive_opts = ["--interactive", "--tty"]
        else:
            interactive_opts = []
        return [self.command, "exec", *interactive_opts, self.container_id]

    def cleanup(self):
        if not self.container_id:
            return
        subprocess.check_call(
            [self.command, "stop", self.container_id], stdout=subprocess.DEVNULL
        )
        super().cleanup()

    def __get_extra_opts__(self):
        opts = os.getenv(self.extra_opts_env_variable, "")
        return shlex.split(opts)

    def get_volume_opts(self):
        volumes = []
        if self.source_dir:
            volumes.append((self.source_dir, self.source_dir))
        if self.output_dir:
            volumes.append((self.output_dir, self.output_dir))
        volumes.append((super().bindir, self.bindir))
        volumes += self.volumes

        return [self.volume(src, dst) for src, dst in volumes]

    def get_metadata(self):
        version = (
            subprocess.check_output([self.command, "--version"]).decode("utf-8").strip()
        )
        image_name = self.get_image()
        image_digest = (
            subprocess.check_output(
                [
                    self.command,
                    "image",
                    "inspect",
                    "--format={{index .RepoDigests 0}}",
                    image_name,
                ],
            )
            .decode("utf-8")
            .strip()
        )
        return {
            "version": version,
            "image_name": image_name,
            "image_digest": image_digest,
        }


class DockerRuntime(ContainerRuntime):
    name = "docker"
    command = "docker"
    extra_opts_env_variable = "TUXMAKE_DOCKER_RUN"

    def get_user_opts(self):
        uid = os.getuid()
        gid = os.getgid()
        return [f"--user={uid}:{gid}"]

    def get_logging_opts(self):
        return []

    def volume(self, source, target):
        return f"--volume={source}:{target}"


class PodmanRuntime(ContainerRuntime):
    name = "podman"
    command = "podman"
    extra_opts_env_variable = "TUXMAKE_PODMAN_RUN"

    def get_user_opts(self):
        return []

    def get_logging_opts(self):
        return ["--log-level=ERROR"]

    def volume(self, source, target):
        return f"--volume={source}:{target}:z"


class LocalMixin:
    prepare_failed_msg = "image {image} not found locally"

    def prepare_image(self):
        subprocess.check_call(
            [self.command, "image", "inspect", self.get_image()],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


class DockerLocalRuntime(LocalMixin, DockerRuntime):
    name = "docker-local"


class PodmanLocalRuntime(LocalMixin, PodmanRuntime):
    name = "podman-local"
