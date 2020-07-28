import subprocess
import pytest

from tuxmake.build import Build
from tuxmake.exceptions import InvalidRuntimeError
from tuxmake.exceptions import RuntimePreparationFailed
from tuxmake.runtime import get_runtime
from tuxmake.runtime import NullRuntime
from tuxmake.runtime import DockerRuntime
from tuxmake.runtime import DockerLocalRuntime
from tuxmake.wrapper import Wrapper


@pytest.fixture
def build(linux):
    b = Build(linux)
    return b


class TestGetRuntime:
    def test_null_runtime(self, build):
        build.docker = False
        assert isinstance(get_runtime(build, None), NullRuntime)

    def test_docker_runtime(self, build):
        assert isinstance(get_runtime(build, "docker"), DockerRuntime)

    def test_invalid_runtime(self, build):
        with pytest.raises(InvalidRuntimeError):
            get_runtime(build, "invalid")
        with pytest.raises(InvalidRuntimeError):
            get_runtime(build, "xyz")


class TestNullRuntime:
    def test_get_command_line(self, build):
        assert NullRuntime(build).get_command_line(["date"]) == ["date"]


@pytest.fixture
def get_docker_image(mocker):
    return mocker.patch("tuxmake.toolchain.Toolchain.get_docker_image")


class TestDockerRuntime:
    def test_docker_image(self, build, get_docker_image):
        get_docker_image.return_value = "foobarbaz"
        runtime = DockerRuntime(build)
        assert runtime.image == "foobarbaz"

    def test_override_docker_image(self, build, monkeypatch):
        monkeypatch.setenv("TUXMAKE_DOCKER_IMAGE", "foobar")
        runtime = DockerRuntime(build)
        assert runtime.image == "foobar"

    def test_prepare(self, build, get_docker_image, mocker):
        get_docker_image.return_value = "myimage"
        check_call = mocker.patch("subprocess.check_call")
        DockerRuntime(build).prepare()
        check_call.assert_called_with(["docker", "pull", "myimage"])

    def test_get_command_line(self, build):
        cmd = DockerRuntime(build).get_command_line(["date"])
        assert cmd[0:2] == ["docker", "run"]
        assert cmd[-1] == "date"

    def test_environment(self, build):
        build.environment = {"FOO": "BAR"}
        cmd = DockerRuntime(build).get_command_line(["date"])
        assert "--env=FOO=BAR" in cmd

    def test_ccache(self, build, home):
        ccache = Wrapper("ccache")
        orig_ccache_dir = ccache.environment["CCACHE_DIR"]
        build.wrapper = ccache
        cmd = DockerRuntime(build).get_command_line(["date"])
        assert "--env=CCACHE_DIR=/ccache-dir" in cmd
        assert f"--volume={orig_ccache_dir}:/ccache-dir" in cmd

    def test_sccache_with_path(self, build, home):
        sccache_from_host = Wrapper("/opt/bin/sccache")
        build.wrapper = sccache_from_host
        cmd = DockerRuntime(build).get_command_line(["date"])
        assert "--volume=/opt/bin/sccache:/usr/local/bin/sccache" in cmd

    def test_TUXMAKE_DOCKER_RUN(self, build, monkeypatch):
        monkeypatch.setenv(
            "TUXMAKE_DOCKER_RUN", "--hostname=foobar --env=FOO='bar baz'"
        )
        cmd = DockerRuntime(build).get_command_line(["bash"])
        assert "--hostname=foobar" in cmd
        assert "--env=FOO=bar baz" in cmd


class TestDockerLocalRuntime:
    def test_prepare_checks_local_image(self, build, get_docker_image, mocker):
        get_docker_image.return_value = "mylocalimage"
        check_call = mocker.patch("subprocess.check_call")
        runtime = DockerLocalRuntime(build)

        runtime.prepare()
        check_call.assert_called_with(
            ["docker", "image", "inspect", mocker.ANY, "mylocalimage"]
        )

    def test_prepare_image_not_found(self, build, get_docker_image, mocker):
        get_docker_image.return_value = "foobar"
        mocker.patch(
            "subprocess.check_call",
            side_effect=subprocess.CalledProcessError(
                1, ["foo"], stderr="Image not found"
            ),
        )
        with pytest.raises(RuntimePreparationFailed) as exc:
            DockerLocalRuntime(build).prepare()
        assert "image foobar not found locally" in str(exc)
