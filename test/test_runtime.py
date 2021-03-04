import subprocess
import pytest

from tuxmake.build import Build
from tuxmake.exceptions import InvalidRuntimeError
from tuxmake.exceptions import RuntimePreparationFailed
from tuxmake.runtime import get_runtime
from tuxmake.runtime import DEFAULT_CONTAINER_REGISTRY
from tuxmake.runtime import Runtime
from tuxmake.runtime import NullRuntime
from tuxmake.runtime import DockerRuntime
from tuxmake.runtime import DockerLocalRuntime
from tuxmake.runtime import PodmanRuntime
from tuxmake.runtime import PodmanLocalRuntime
from tuxmake.wrapper import Wrapper


@pytest.fixture
def build(linux):
    b = Build(linux)
    return b


class TestGetRuntime:
    def test_null_runtime(self):
        assert isinstance(get_runtime(None), NullRuntime)

    def test_docker_runtime(self):
        assert isinstance(get_runtime("docker"), DockerRuntime)

    def test_docker_local_runtime(self):
        assert isinstance(get_runtime("docker-local"), DockerLocalRuntime)

    def test_invalid_runtime(self):
        with pytest.raises(InvalidRuntimeError):
            get_runtime("invalid")
        with pytest.raises(InvalidRuntimeError):
            get_runtime("xyz")


class TestRuntime:
    def test_invalid_runtime(self, monkeypatch):
        monkeypatch.setattr(Runtime, "name", "invalid")
        with pytest.raises(InvalidRuntimeError):
            Runtime()


class TestNullRuntime:
    def test_get_command_line(self, build):
        assert NullRuntime().get_command_line(build, ["date"], False) == ["date"]

    def test_prepare_warns_about_versioned_toolchain(self, build, mocker):
        build.toolchain.version_suffix = "-10"
        log = mocker.patch("tuxmake.build.Build.log")
        runtime = NullRuntime()
        runtime.prepare(build)
        log.assert_called()

    def test_toolchains(self):
        runtime = NullRuntime()
        assert "gcc" in runtime.toolchains


@pytest.fixture
def get_image(mocker):
    return mocker.patch("tuxmake.toolchain.Toolchain.get_image")


def q(img):
    return f"{DEFAULT_CONTAINER_REGISTRY}/{img}"


class TestDockerRuntime:
    def test_image(self, build, get_image):
        get_image.return_value = "foobarbaz"
        runtime = DockerRuntime()
        assert runtime.get_image(build) == q("foobarbaz")

    def test_override_image(self, build, monkeypatch):
        monkeypatch.setenv("TUXMAKE_IMAGE", "foobar")
        runtime = DockerRuntime()
        assert runtime.get_image(build) == q("foobar")

    def test_override_image_registry(self, build, monkeypatch, get_image):
        monkeypatch.setenv("TUXMAKE_IMAGE_REGISTRY", "foobar.com")
        get_image.return_value = "myimage"
        runtime = DockerRuntime()
        assert runtime.get_image(build) == "foobar.com/myimage"

    def test_override_image_tag(self, build, monkeypatch, get_image):
        monkeypatch.setenv("TUXMAKE_IMAGE_TAG", "20201201")
        get_image.return_value = "myimage"
        runtime = DockerRuntime()
        assert runtime.get_image(build) == q("myimage:20201201")

    def test_override_image_registry_and_tag(self, build, monkeypatch, get_image):
        monkeypatch.setenv("TUXMAKE_IMAGE_REGISTRY", "foobar.com")
        monkeypatch.setenv("TUXMAKE_IMAGE_TAG", "20201201")
        get_image.return_value = "myimage"
        runtime = DockerRuntime()
        assert runtime.get_image(build) == "foobar.com/myimage:20201201"

    def test_override_full_image_name_with_registry(self, build, monkeypatch):
        monkeypatch.setenv("TUXMAKE_IMAGE", "docker.io/foo/bar")
        runtime = DockerRuntime()
        assert runtime.get_image(build) == "docker.io/foo/bar"

    def test_prepare(self, build, get_image, mocker):
        get_image.return_value = "myimage"
        check_call = mocker.patch("subprocess.check_call")
        DockerRuntime().prepare(build)
        check_call.assert_called_with(["docker", "pull", q("myimage")])

    def test_prepare_pull_only_once_a_day(self, build, get_image, mocker):
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
        PodmanRuntime().prepare(build)
        assert len(check_call.call_args_list) == 1

        # after 2 hours, no need to pull
        PodmanRuntime().prepare(build)
        assert len(check_call.call_args_list) == 1

        # after 2 days, pull again
        PodmanRuntime().prepare(build)
        assert len(check_call.call_args_list) == 2

    def test_get_command_line(self, build):
        cmd = DockerRuntime().get_command_line(build, ["date"], False)
        assert cmd[0:2] == ["docker", "run"]
        assert cmd[-1] == "date"

    def test_environment(self, build):
        build.environment = {"FOO": "BAR"}
        cmd = DockerRuntime().get_command_line(build, ["date"], False)
        assert "--env=FOO=BAR" in cmd

    def test_ccache(self, build, home):
        ccache = Wrapper("ccache")
        orig_ccache_dir = ccache.environment["CCACHE_DIR"]
        build.wrapper = ccache
        cmd = DockerRuntime().get_command_line(build, ["date"], False)
        assert "--env=CCACHE_DIR=/ccache-dir" in cmd
        assert f"--volume={orig_ccache_dir}:/ccache-dir" in cmd

    def test_sccache_with_path(self, build, home):
        sccache_from_host = Wrapper("/opt/bin/sccache")
        build.wrapper = sccache_from_host
        cmd = DockerRuntime().get_command_line(build, ["date"], False)
        assert "--volume=/opt/bin/sccache:/usr/local/bin/sccache" in cmd

    def test_TUXMAKE_DOCKER_RUN(self, build, monkeypatch):
        monkeypatch.setenv(
            "TUXMAKE_DOCKER_RUN", "--hostname=foobar --env=FOO='bar baz'"
        )
        cmd = DockerRuntime().get_command_line(build, ["bash"], False)
        assert "--hostname=foobar" in cmd
        assert "--env=FOO=bar baz" in cmd

    def test_interactive(self, build):
        cmd = DockerRuntime().get_command_line(build, ["bash"], True)
        assert "--interactive" in cmd
        assert "--tty" in cmd

    def test_bases(self):
        assert [
            t.name
            for t in DockerRuntime().base_images
            if not t.name.startswith("base-debian")
        ] == []

    def test_ci_images(self):
        assert "ci-python3.8" in [t.name for t in DockerRuntime().ci_images]

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


class TestDockerLocalRuntime:
    def test_prepare_checks_local_image(self, build, get_image, mocker):
        get_image.return_value = "mylocalimage"
        check_call = mocker.patch("subprocess.check_call")
        runtime = DockerLocalRuntime()

        runtime.prepare(build)
        check_call.assert_called_with(
            ["docker", "image", "inspect", q("mylocalimage")],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def test_prepare_image_not_found(self, build, get_image, mocker):
        get_image.return_value = "foobar"
        mocker.patch(
            "subprocess.check_call",
            side_effect=subprocess.CalledProcessError(
                1, ["foo"], stderr="Image not found"
            ),
        )
        with pytest.raises(RuntimePreparationFailed) as exc:
            DockerLocalRuntime().prepare(build)
        assert f"image {q('foobar')} not found locally" in str(exc)

    def test_listed_as_supported(self):
        assert "docker-local" in Runtime.supported()

    def test_str(self):
        assert str(DockerLocalRuntime()) == "docker-local"


class TestPodmanRuntime:
    def test_prepare(self, build, get_image, mocker):
        get_image.return_value = "myimage"
        check_call = mocker.patch("subprocess.check_call")
        PodmanRuntime().prepare(build)
        check_call.assert_called_with(["podman", "pull", q("myimage")])

    def test_get_command_line(self, build):
        cmd = PodmanRuntime().get_command_line(build, ["date"], False)
        assert cmd[0:2] == ["podman", "run"]
        assert cmd[-1] == "date"

    def test_listed_as_supported(self):
        assert "podman" in Runtime.supported()

    def test_no_user_option(self, build):
        cmd = PodmanRuntime().get_command_line(build, ["date"], False)
        assert len([c for c in cmd if "--user=" in c]) == 0

    def test_str(self):
        assert str(PodmanRuntime()) == "podman"

    def test_TUXMAKE_PODMAN_RUN(self, build, monkeypatch):
        monkeypatch.setenv(
            "TUXMAKE_PODMAN_RUN", "--hostname=foobar --env=FOO='bar baz'"
        )
        cmd = PodmanRuntime().get_command_line(build, ["bash"], False)
        assert "--hostname=foobar" in cmd
        assert "--env=FOO=bar baz" in cmd

    def test_selinux_label(self, build):
        cmd = PodmanRuntime().get_command_line(build, ["bash"], False)
        volumes = [o for o in cmd if o.startswith("--volume=")]
        assert all([v.endswith(":z") for v in volumes])

    def test_logging_level(self, build):
        cmd = PodmanRuntime().get_command_line(build, ["bash"], False)
        assert "--log-level=ERROR" in cmd


class TestPodmanLocalRuntime:
    def test_prepare_checks_local_image(self, build, get_image, mocker):
        get_image.return_value = "mylocalimage"
        check_call = mocker.patch("subprocess.check_call")
        runtime = PodmanLocalRuntime()

        runtime.prepare(build)
        check_call.assert_called_with(
            ["podman", "image", "inspect", q("mylocalimage")],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def test_prepare_image_not_found(self, build, get_image, mocker):
        get_image.return_value = "foobar"
        mocker.patch(
            "subprocess.check_call",
            side_effect=subprocess.CalledProcessError(
                1, ["foo"], stderr="Image not found"
            ),
        )
        with pytest.raises(RuntimePreparationFailed) as exc:
            PodmanLocalRuntime().prepare(build)
        assert f"image {q('foobar')} not found locally" in str(exc)

    def test_listed_as_supported(self):
        assert "podman-local" in Runtime.supported()

    def test_str(self):
        assert str(PodmanLocalRuntime()) == "podman-local"
