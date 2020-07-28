import os
import re
import shlex
import subprocess
import sys


from tuxmake.exceptions import RuntimePreparationFailed
from tuxmake.exceptions import InvalidRuntimeError


DEFAULT_RUNTIME = "null"


def get_runtime(build, runtime):
    runtime = runtime or DEFAULT_RUNTIME
    name = "".join([w.title() for w in re.split(r"[_-]", runtime)]) + "Runtime"
    try:
        here = sys.modules[__name__]
        cls = getattr(here, name)
        return cls(build)
    except AttributeError:
        raise InvalidRuntimeError(runtime)


class Runtime:
    def __init__(self, build):
        self.build = build

    def get_command_line(self, cmd):
        return cmd

    def prepare(self):
        try:
            self.do_prepare()
        except subprocess.CalledProcessError:
            raise RuntimePreparationFailed(
                self.prepare_failed_msg.format(image=self.image)
            )

    def do_prepare(self):
        pass


class NullRuntime(Runtime):
    pass


class DockerRuntime(Runtime):
    def __init__(self, build):
        super().__init__(build)
        self.image = os.getenv("TUXMAKE_DOCKER_IMAGE")
        if not self.image:
            self.image = build.toolchain.get_docker_image(build.target_arch)

    prepare_failed_msg = "failed to pull remote image {image}"

    def do_prepare(self):
        subprocess.check_call(["docker", "pull", self.image])

    def get_command_line(self, cmd):
        build = self.build
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

        env = (f"--env={k}={v}" for k, v in build.environment.items())
        uid = os.getuid()
        gid = os.getgid()
        extra_opts = self.__get_extra_opts__()
        return [
            "docker",
            "run",
            "--rm",
            "--init",
            *wrapper_opts,
            *env,
            f"--user={uid}:{gid}",
            f"--volume={source_tree}:{source_tree}",
            f"--volume={build_dir}:{build_dir}",
            f"--workdir={source_tree}",
            *extra_opts,
            self.image,
        ] + cmd

    def __get_extra_opts__(self):
        opts = os.getenv("TUXMAKE_DOCKER_RUN", "")
        return shlex.split(opts)


class DockerLocalRuntime(DockerRuntime):
    prepare_failed_msg = "image {image} not found locally"

    def do_prepare(self):
        subprocess.check_call(
            [
                "docker",
                "image",
                "inspect",
                f"--format=Local image {self.image} exists!",
                self.image,
            ]
        )
