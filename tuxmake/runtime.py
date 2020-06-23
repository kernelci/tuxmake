import os
import subprocess


def get_runtime(build, runtime):
    if runtime == "docker":
        return DockerRuntime(build)
    else:
        return NullRuntime()


class NullRuntime:
    def get_command_line(self, cmd):
        return cmd

    def prepare(self):
        pass


class DockerRuntime:
    def __init__(self, build):
        self.build = build
        self.image = os.getenv("TUXMAKE_DOCKER_IMAGE")
        if not self.image:
            self.image = build.toolchain.get_docker_image(build.target_arch)

    def prepare(self):
        subprocess.check_call(["docker", "pull", self.image])

    def get_command_line(self, cmd):
        build = self.build
        source_tree = os.path.abspath(build.source_tree)
        build_dir = os.path.abspath(build.build_dir)

        uid = os.getuid()
        gid = os.getgid()
        return [
            "docker",
            "run",
            "--rm",
            f"--user={uid}:{gid}",
            f"--volume={source_tree}:{source_tree}",
            f"--volume={build_dir}:{build_dir}",
            f"--workdir={source_tree}",
            self.image,
        ] + cmd
