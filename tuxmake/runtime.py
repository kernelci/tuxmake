import os
import re
import shlex
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path


from tuxmake import cache
from tuxmake import deprecated
from tuxmake.logging import debug, warning
from tuxmake.config import ConfigurableObject, split, splitmap, splitlistmap
from tuxmake.exceptions import RuntimePreparationFailed
from tuxmake.exceptions import InvalidRuntimeError
from tuxmake.toolchain import Toolchain
from tuxmake.arch import host_arch


DEFAULT_RUNTIME = "null"
DEFAULT_CONTAINER_REGISTRY = "docker.io"


def get_runtime(runtime):
    runtime = runtime or DEFAULT_RUNTIME
    name = "".join([w.title() for w in re.split(r"[_-]", runtime)]) + "Runtime"
    try:
        here = sys.modules[__name__]
        cls = getattr(here, name)
        return cls()
    except AttributeError:
        raise InvalidRuntimeError(runtime)


class Runtime(ConfigurableObject):
    basedir = "runtime"
    name = "runtime"
    exception = InvalidRuntimeError

    def __init__(self):
        super().__init__(self.name)
        self.__offline_available__ = None

    def __init_config__(self):
        self.toolchains = Toolchain.supported()

    def get_image(self, build):
        return None

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
                warning(f"W: offline builds not available ({error})")
                self.__offline_available__ = False
        return self.__offline_available__

    def get_command_line(self, build, cmd, interactive, offline=True):
        prefix = self.get_command_prefix(interactive)
        if offline and self.offline_available:
            go_offline = [str(self.get_go_offline_command())]
        else:
            go_offline = []
        return [*prefix, *go_offline, *cmd]

    def get_command_prefix(self, interactive):
        return []

    def prepare(self, build):
        pass

    def cleanup(self):
        pass

    def get_go_offline_command(self):
        return Path(__file__).parent / self.basedir / "tuxmake-offline-build"

    def get_check_environment_command(self):
        return Path(__file__).parent / self.basedir / "tuxmake-check-environment"


class NullRuntime(Runtime):
    name = "null"

    def prepare(self, build):
        super().prepare(build)
        toolchain = build.toolchain
        if toolchain.version_suffix:
            compiler = toolchain.compiler(build.target_arch)
            build.log(
                f"W: Requested {toolchain}, but versioned toolchains are not supported by the null runtime. Will use whatever version of {compiler} that you have installed. To ensure {toolchain} is used, try use a container-based runtime instead."
            )


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
        self.packages = split(packages)
        self.install_options = install_options
        self.rebuild = rebuild
        self.extra_apt_repo = extra_apt_repo
        self.extra_apt_repo_key = extra_apt_repo_key


class ContainerRuntime(Runtime):
    prepare_failed_msg = "failed to pull remote image {image}"

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
                    cross_image = Image(
                        name=f"{target}_{image.name}", group=group, **cross_config
                    )
                    image_list.append(cross_image)
        self.images = self.base_images + self.ci_images + self.toolchain_images
        self.toolchain_images_map = {
            f"tuxmake/{image.name}": image for image in self.toolchain_images
        }
        self.container_id = None

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

    @lru_cache(None)
    def get_image(self, build):
        image = (
            os.getenv("TUXMAKE_IMAGE")
            or deprecated.getenv("TUXMAKE_DOCKER_IMAGE", "TUXMAKE_IMAGE")
            or build.target_arch.get_image(build.toolchain)
            or build.toolchain.get_image(build.target_arch)
        )
        registry = os.getenv("TUXMAKE_IMAGE_REGISTRY", DEFAULT_CONTAINER_REGISTRY)
        if registry:
            if len(image.split("/")) < 3:
                # only prepend registry if the image name is not already a full
                # image name.
                image = registry + "/" + image
        tag = os.getenv("TUXMAKE_IMAGE_TAG")
        if tag:
            image = image + ":" + tag
        return image

    def prepare(self, build):
        super().prepare(build)
        try:
            self.prepare_image(build)
            self.start_container(build)
        except subprocess.CalledProcessError:
            raise RuntimePreparationFailed(
                self.prepare_failed_msg.format(image=self.get_image(build))
            )

    def prepare_image(self, build):
        pull = [self.command, "pull", self.get_image(build)]
        last_pull = cache.get(pull)
        now = time.time()
        if last_pull:
            a_day_ago = now - (24 * 60 * 60)
            if last_pull > a_day_ago:
                return
        subprocess.check_call(pull)
        cache.set(pull, time.time())

    def start_container(self, build):
        source_tree = os.path.abspath(build.source_tree)
        build_dir = os.path.abspath(build.build_dir)

        wrapper = build.wrapper
        wrapper_opts = []
        if wrapper.path:
            wrapper_opts.append(
                f"--volume={wrapper.path}:/usr/local/bin/{wrapper.name}"
            )
        for k, v in wrapper.environment.items():
            if k.endswith("_DIR"):
                path = "/" + re.sub(r"[^a-zA-Z0-9]+", "-", k.lower())
                wrapper_opts.append(f"--volume={v}:{path}")
                v = path
            wrapper_opts.append(f"--env={k}={v}")

        orig_go_offline = super().get_go_offline_command()
        go_offline = self.get_go_offline_command()
        go_offline_volume = self.volume(orig_go_offline, f"/usr/local/bin/{go_offline}")
        orig_check_environment = super().get_check_environment_command()
        check_environment = self.get_check_environment_command()
        check_environment_volume = self.volume(
            orig_check_environment, f"/usr/local/bin/{check_environment}"
        )

        env = (f"--env={k}={v}" for k, v in build.environment.items())
        user_opts = self.get_user_opts()
        extra_opts = self.__get_extra_opts__()
        cmd = [
            self.command,
            "run",
            "--rm",
            "--init",
            "--detach",
            *wrapper_opts,
            "--env=KBUILD_BUILD_USER=tuxmake",
            *env,
            *user_opts,
            self.volume(source_tree, source_tree),
            self.volume(build_dir, build_dir),
            go_offline_volume,
            check_environment_volume,
            f"--workdir={source_tree}",
            *self.get_logging_opts(),
            *extra_opts,
            self.get_image(build),
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

    def get_go_offline_command(self):
        return super().get_go_offline_command().name

    def get_check_environment_command(self):
        return super().get_check_environment_command().name

    def cleanup(self):
        if not self.container_id:
            return
        subprocess.check_call(
            [self.command, "stop", self.container_id], stdout=subprocess.DEVNULL
        )

    def __get_extra_opts__(self):
        opts = os.getenv(self.extra_opts_env_variable, "")
        return shlex.split(opts)


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

    def prepare_image(self, build):
        subprocess.check_call(
            [self.command, "image", "inspect", self.get_image(build)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


class DockerLocalRuntime(LocalMixin, DockerRuntime):
    name = "docker-local"


class PodmanLocalRuntime(LocalMixin, PodmanRuntime):
    name = "podman-local"
