import re
import subprocess
import pytest

from tuxmake.build import Build
from tuxmake.exceptions import InvalidRuntimeError
from tuxmake.exceptions import RuntimePreparationFailed
from tuxmake.runtime import Runtime
from tuxmake.runtime import NullRuntime
from tuxmake.runtime import DockerRuntime
from tuxmake.runtime import DockerLocalRuntime
from tuxmake.runtime import PodmanRuntime
from tuxmake.runtime import PodmanLocalRuntime
from tuxmake.runtime import Terminated


@pytest.fixture
def build(linux):
    b = Build(linux)
    return b


class TestTerminated:
    def test_basics(self):
        with pytest.raises(Terminated):
            Terminated.handle_signal(9, "BOOM")


class TestGetRuntime:
    def test_null_runtime(self):
        assert isinstance(Runtime.get(None), NullRuntime)

    def test_docker_runtime(self):
        assert isinstance(Runtime.get("docker"), DockerRuntime)

    def test_docker_local_runtime(self):
        assert isinstance(Runtime.get("docker-local"), DockerLocalRuntime)

    def test_invalid_runtime(self):
        with pytest.raises(InvalidRuntimeError):
            Runtime.get("invalid")
        with pytest.raises(InvalidRuntimeError):
            Runtime.get("xyz")


class TestRuntime:
    def test_invalid_runtime(self, monkeypatch):
        monkeypatch.setattr(Runtime, "name", "invalid")
        with pytest.raises(InvalidRuntimeError):
            Runtime()

    def test_run_cmd_interactive(self, Popen, mocker):
        get_command_line = mocker.patch(
            "tuxmake.runtime.Runtime.get_command_line", return_value=["/bin/bash"]
        )
        runtime = NullRuntime()
        runtime.run_cmd(["/bin/bash"], interactive=True)
        kwargs = Popen.call_args[1]
        get_command_line.assert_called_with(
            ["/bin/bash"], interactive=True, offline=True
        )
        assert kwargs["stdin"] is None
        assert kwargs["stdout"] is None
        assert kwargs["stderr"] is None


class TestNullRuntime:
    def test_get_command_line(self, build):
        assert NullRuntime().get_command_line(
            ["date"], interactive=False, offline=False
        ) == ["date"]

    def test_toolchains(self):
        runtime = NullRuntime()
        assert "gcc" in runtime.toolchains


@pytest.fixture
def container_id():
    return "0123456789abcdef"


class FakeGetImage:
    @pytest.fixture(autouse=True)
    def get_image(self, mocker):
        return mocker.patch("tuxmake.runtime.Runtime.get_image")


class TestContainerRuntime(FakeGetImage):
    @pytest.fixture(autouse=True)
    def spawn_container(self, mocker, container_id):
        return mocker.patch(
            "tuxmake.runtime.ContainerRuntime.spawn_container",
            return_value=container_id,
        )

    @pytest.fixture(autouse=True)
    def offline_available(self, mocker):
        return mocker.patch(
            "tuxmake.runtime.Runtime.offline_available", return_value=False
        )


class TestGetImage:
    def test_no_image(self):
        runtime = NullRuntime()
        with pytest.raises(Exception):
            runtime.get_image()

    def test_with_image(self):
        runtime = NullRuntime()
        runtime.set_image("myimage")
        assert runtime.get_image() == "myimage"


class TestDockerRuntime(TestContainerRuntime):
    def test_get_metadata(self, get_image, mocker):
        get_image.return_value = "tuxmake/theimage"
        mocker.patch(
            "subprocess.check_output",
            return_value=b"tuxmake/theimage@sha256:deadbeef",
        )
        metadata = DockerRuntime().get_metadata()
        assert metadata["image_name"] == "tuxmake/theimage"
        assert metadata["image_digest"] == "tuxmake/theimage@sha256:deadbeef"

    def test_prepare(self, get_image, mocker):
        get_image.return_value = "myimage"
        check_call = mocker.patch("subprocess.check_call")
        DockerRuntime().prepare()
        check_call.assert_called_with(["docker", "pull", "myimage"])

    def test_prepare_pull_only_once_a_day(self, get_image, mocker):
        get_image.return_value = "myimage"
        check_call = mocker.patch("subprocess.check_call")
        now = 1614000983
        mocker.patch("time.time", return_value=now)
        two_hours_ago = now - (2 * 60 * 60)
        two_days_ago = now - (2 * 24 * 60 * 60)
        mocker.patch(
            "tuxmake.cache.get", side_effect=(None, two_hours_ago, two_days_ago)
        )

        # first call
        PodmanRuntime().prepare()
        assert len(check_call.call_args_list) == 1

        # after 2 hours, no need to pull
        PodmanRuntime().prepare()
        assert len(check_call.call_args_list) == 1

        # after 2 days, pull again
        PodmanRuntime().prepare()
        assert len(check_call.call_args_list) == 2

    def test_start_container(self, container_id):
        runtime = DockerRuntime()
        runtime.start_container()
        assert runtime.container_id == container_id

    def test_cleanup(self, container_id, mocker):
        check_call = mocker.patch("subprocess.check_call")
        runtime = DockerRuntime()
        runtime.start_container()
        runtime.cleanup()
        cmd = check_call.call_args[0][0]
        assert cmd[0:2] == ["docker", "stop"]
        assert cmd[-1] == container_id

    def test_cleanup_before_container_exists(self):
        runtime = DockerRuntime()
        assert runtime.container_id is None
        runtime.cleanup()  # if this doesn't crash we are good

    def test_get_command_line(self):
        cmd = DockerRuntime().get_command_line(["date"], False)
        assert cmd[0:2] == ["docker", "exec"]
        assert cmd[-1] == "date"

    def test_environment(self, linux, spawn_container):
        runtime = DockerRuntime()
        runtime.environment["FOO"] = "BAR"
        runtime.start_container()
        cmd = spawn_container.call_args[0][0]
        assert "--env=FOO=BAR" in cmd

    def test_output_dir(self, linux, tmp_path, spawn_container):
        runtime = DockerRuntime()
        runtime.output_dir = tmp_path
        runtime.start_container()
        cmd = spawn_container.call_args[0][0]
        assert f"--volume={tmp_path}:{tmp_path}" in cmd

    def test_source_dir(self, linux, tmp_path, spawn_container):
        runtime = DockerRuntime()
        runtime.source_dir = tmp_path
        runtime.start_container()
        cmd = spawn_container.call_args[0][0]
        assert f"--volume={tmp_path}:{tmp_path}" in cmd

    def test_volume(self, linux, spawn_container):
        runtime = DockerRuntime()
        path = "/path/to/something"
        runtime.add_volume(path)
        runtime.start_container()
        cmd = spawn_container.call_args[0][0]
        assert f"--volume={path}:{path}" in cmd

    def test_TUXMAKE_DOCKER_RUN(self, monkeypatch, spawn_container):
        monkeypatch.setenv(
            "TUXMAKE_DOCKER_RUN", "--hostname=foobar --env=FOO='bar baz'"
        )
        DockerRuntime().start_container()
        cmd = spawn_container.call_args[0][0]
        assert "--hostname=foobar" in cmd
        assert "--env=FOO=bar baz" in cmd

    def test_interactive(self):
        cmd = DockerRuntime().get_command_line(["bash"], True)
        assert "--interactive" in cmd
        assert "--tty" in cmd

    def test_bases(self):
        assert [
            t.name
            for t in DockerRuntime().base_images
            if not t.name.startswith("base-debian")
        ] == []

    def test_toolchain_images(self):
        images = [t.name for t in DockerRuntime().toolchain_images]
        assert "gcc" in images
        assert "clang" in images

    def test_toolchains(self):
        toolchains = DockerRuntime().toolchains
        assert "gcc" in toolchains
        assert "clang" in toolchains
        assert "llvm" in toolchains

    def test_listed_as_supported(self):
        assert "docker" in Runtime.supported()

    def test_str(self):
        assert str(DockerRuntime()) == "docker"


class TestDockerRuntimeSpawnContainer(FakeGetImage):
    def test_spawn_container(self, mocker, container_id):
        check_output = mocker.patch(
            "subprocess.check_output", return_value=container_id.encode("utf-8")
        )
        runtime = DockerRuntime()
        runtime.start_container()
        cmd = check_output.call_args[0][0]
        assert cmd[0:2] == ["docker", "run"]
        assert runtime.container_id == container_id


class TestDockerRuntimeOfflineAvailable(FakeGetImage):
    @pytest.fixture
    def runtime(self, container_id, mocker):
        mocker.patch(
            "tuxmake.runtime.DockerRuntime.spawn_container", return_value=container_id
        )
        mocker.patch("tuxmake.runtime.ContainerRuntime.prepare_image")
        r = DockerRuntime()
        r.prepare()
        return r

    def test_offline_available(self, runtime, mocker):
        mocker.patch("subprocess.check_output")
        assert runtime.offline_available

    def test_offline_not_available(self, runtime, mocker, capsys):
        mocker.patch(
            "subprocess.check_output",
            side_effect=subprocess.CalledProcessError(
                1, ["true"], output=b"some error"
            ),
        )
        assert not runtime.offline_available
        _, stderr = capsys.readouterr()
        assert re.match("W:.*(some error)", stderr)


class TestDockerLocalRuntime(TestContainerRuntime):
    def test_prepare_checks_local_image(self, get_image, mocker):
        get_image.return_value = "mylocalimage"
        check_call = mocker.patch("subprocess.check_call")
        runtime = DockerLocalRuntime()

        runtime.prepare()
        check_call.assert_called_with(
            ["docker", "image", "inspect", "mylocalimage"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def test_prepare_image_not_found(self, get_image, mocker):
        get_image.return_value = "foobar"
        mocker.patch(
            "subprocess.check_call",
            side_effect=subprocess.CalledProcessError(
                1, ["foo"], stderr="Image not found"
            ),
        )
        with pytest.raises(RuntimePreparationFailed) as exc:
            DockerLocalRuntime().prepare()
        assert "image foobar not found locally" in str(exc)

    def test_listed_as_supported(self):
        assert "docker-local" in Runtime.supported()

    def test_str(self):
        assert str(DockerLocalRuntime()) == "docker-local"


class TestPodmanRuntime(TestContainerRuntime):
    def test_prepare(self, get_image, mocker):
        get_image.return_value = "myimage"
        check_call = mocker.patch("subprocess.check_call")
        PodmanRuntime().prepare()
        check_call.assert_called_with(["podman", "pull", "myimage"])

    def test_get_command_line(self):
        cmd = PodmanRuntime().get_command_line(["date"], False)
        assert cmd[0:2] == ["podman", "exec"]
        assert cmd[-1] == "date"

    def test_listed_as_supported(self):
        assert "podman" in Runtime.supported()

    def test_no_user_option(self, get_image, spawn_container):
        PodmanRuntime().start_container()
        cmd = spawn_container.call_args[0][0]
        assert len([c for c in cmd if "--user=" in c]) == 0

    def test_str(self):
        assert str(PodmanRuntime()) == "podman"

    def test_TUXMAKE_PODMAN_RUN(self, monkeypatch, spawn_container):
        monkeypatch.setenv(
            "TUXMAKE_PODMAN_RUN", "--hostname=foobar --env=FOO='bar baz'"
        )
        PodmanRuntime().start_container()
        cmd = spawn_container.call_args[0][0]
        assert "--hostname=foobar" in cmd
        assert "--env=FOO=bar baz" in cmd

    def test_selinux_label(self, get_image, spawn_container):
        PodmanRuntime().start_container()
        cmd = spawn_container.call_args[0][0]
        volumes = [o for o in cmd if o.startswith("--volume=")]
        assert all([v.endswith(":z") for v in volumes])

    def test_logging_level(self, spawn_container):
        PodmanRuntime().start_container()
        cmd = spawn_container.call_args[0][0]
        assert "--log-level=ERROR" in cmd


class TestPodmanLocalRuntime(TestContainerRuntime):
    def test_prepare_checks_local_image(self, get_image, mocker):
        get_image.return_value = "mylocalimage"
        check_call = mocker.patch("subprocess.check_call")
        runtime = PodmanLocalRuntime()

        runtime.prepare()
        check_call.assert_called_with(
            ["podman", "image", "inspect", "mylocalimage"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def test_prepare_image_not_found(self, get_image, mocker):
        get_image.return_value = "foobar"
        mocker.patch(
            "subprocess.check_call",
            side_effect=subprocess.CalledProcessError(
                1, ["foo"], stderr="Image not found"
            ),
        )
        with pytest.raises(RuntimePreparationFailed) as exc:
            PodmanLocalRuntime().prepare()
        assert "image foobar not found locally" in str(exc)

    def test_listed_as_supported(self):
        assert "podman-local" in Runtime.supported()

    def test_str(self):
        assert str(PodmanLocalRuntime()) == "podman-local"
