import os
import re
import shlex
import subprocess
import sys


from tuxmake.config import ConfigurableObject, split, splitmap, splitlistmap
from tuxmake.exceptions import RuntimePreparationFailed
from tuxmake.exceptions import InvalidRuntimeError
from tuxmake.toolchain import Toolchain
from tuxmake.arch import host_arch


DEFAULT_RUNTIME = "null"


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
    exception = InvalidRuntimeError
    not_aliases = ["docker-local.ini"]

    def __init__(self):
        super().__init__(self.name)

    def __init_config__(self):
        self.toolchains = Toolchain.supported()

    def is_supported(self, arch, toolchain):
        return True

    def get_command_line(self, build, cmd, interactive):
        return cmd

    def prepare(self, build):
        pass


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
        targets="",
        target_bases="",
        target_kinds="",
        target_hosts="",
        packages="",
    ):
        self.name = name
        self.kind = kind
        self.base = base
        self.hosts = split(hosts)
        self.targets = split(targets)
        self.target_bases = splitmap(target_bases)
        self.target_kinds = splitmap(target_kinds)
        self.target_hosts = splitlistmap(target_hosts)
        self.packages = split(packages)
        self.rebuild = rebuild


class DockerRuntime(Runtime):
    name = "docker"
    command = "docker"
    prepare_failed_msg = "failed to pull remote image {image}"

    def __init_config__(self):
        self.base_images = []
        self.ci_images = []
        self.toolchain_images = []
        self.toolchains = split(self.config["runtime"]["toolchains"])
        for image_list, config in (
            (self.base_images, self.config["runtime"]["bases"]),
            (self.ci_images, self.config["runtime"]["ci"]),
            (self.toolchain_images, self.toolchains),
        ):
            for entry in split(config):
                if entry not in self.config:
                    continue
                image = Image(name=entry, **self.config[entry])
                image_list.append(image)
                for target in image.targets:
                    cross_config = dict(self.config[entry])
                    cross_config["base"] = image.target_bases.get(target, image.name)
                    cross_config["kind"] = image.target_kinds.get(
                        target, "cross-" + image.kind
                    )
                    cross_config["hosts"] = image.target_hosts.get(target, image.hosts)
                    cross_image = Image(name=f"{target}_{image.name}", **cross_config)
                    image_list.append(cross_image)
        self.images = self.base_images + self.ci_images + self.toolchain_images
        self.toolchain_images_map = {
            f"tuxmake/{image.name}": image for image in self.toolchain_images
        }

    def is_supported(self, arch, toolchain):
        image_name = toolchain.get_docker_image(arch)
        image = self.toolchain_images_map.get(image_name)
        if image:
            return host_arch.name in image.hosts or any(
                [a in image.hosts for a in host_arch.aliases]
            )
        else:
            return False

    def get_image(self, build):
        return os.getenv("TUXMAKE_DOCKER_IMAGE") or build.toolchain.get_docker_image(
            build.target_arch
        )

    def prepare(self, build):
        super().prepare(build)
        try:
            self.do_prepare(build)
        except subprocess.CalledProcessError:
            raise RuntimePreparationFailed(
                self.prepare_failed_msg.format(image=self.get_image(build))
            )

    def do_prepare(self, build):
        subprocess.check_call([self.command, "pull", self.get_image(build)])

    def get_command_line(self, build, cmd, interactive):
        source_tree = os.path.abspath(build.source_tree)
        build_dir = os.path.abspath(build.build_dir)

        if interactive:
            interactive_opts = ["--interactive", "--tty"]
        else:
            interactive_opts = []

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

        env = (f"--env={k}={v}" for k, v in build.environment.items())
        uid = os.getuid()
        gid = os.getgid()
        extra_opts = self.__get_extra_opts__()
        return [
            self.command,
            "run",
            "--rm",
            "--init",
            *interactive_opts,
            *wrapper_opts,
            "--env=KBUILD_BUILD_USER=tuxmake",
            *env,
            f"--user={uid}:{gid}",
            f"--volume={source_tree}:{source_tree}",
            f"--volume={build_dir}:{build_dir}",
            f"--workdir={source_tree}",
            *extra_opts,
            self.get_image(build),
        ] + cmd

    def __get_extra_opts__(self):
        opts = os.getenv("TUXMAKE_DOCKER_RUN", "")
        return shlex.split(opts)


class DockerLocalRuntime(DockerRuntime):
    name = "docker-local"
    prepare_failed_msg = "image {image} not found locally"

    def do_prepare(self, build):
        subprocess.check_call(
            [self.command, "image", "inspect", self.get_image(build)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
