import pytest

from tuxmake.build import Build
from tuxmake.runtime import get_runtime
from tuxmake.runtime import NullRuntime
from tuxmake.runtime import DockerRuntime


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


class TestNullRuntime:
    def test_get_command_line(self):
        assert NullRuntime().get_command_line(["date"]) == ["date"]


class TestDockerRuntime:
    def test_docker_image(self, build, mocker):
        get_docker_image = mocker.patch("tuxmake.toolchain.Toolchain.get_docker_image")
        get_docker_image.return_value = "foobarbaz"
        runtime = DockerRuntime(build)
        assert runtime.image == "foobarbaz"

    def test_override_docker_image(self, build, monkeypatch):
        monkeypatch.setenv("TUXMAKE_DOCKER_IMAGE", "foobar")
        runtime = DockerRuntime(build)
        assert runtime.image == "foobar"

    def test_prepare(self, build, mocker):
        check_call = mocker.patch("subprocess.check_call")
        DockerRuntime(build).prepare()
        check_call.assert_called_with(["docker", "pull", mocker.ANY])

    def test_get_command_line(self, build):
        cmd = DockerRuntime(build).get_command_line(["date"])
        assert cmd[0:2] == ["docker", "run"]
        assert cmd[-1] == "date"
