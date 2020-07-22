import subprocess
import pytest

from tuxmake.build import Build
from tuxmake.exceptions import InvalidRuntimeError
from tuxmake.exceptions import RuntimePreparationFailed
from tuxmake.runtime import get_runtime
from tuxmake.runtime import NullRuntime
from tuxmake.runtime import DockerRuntime
from tuxmake.runtime import DockerLocalRuntime


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
