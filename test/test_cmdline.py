import pytest
from tuxmake.cmdline import CommandLine
from tuxmake.build import Build


@pytest.fixture
def cmdline():
    return CommandLine()


class TestCommandLine:
    def test_tuxmake(self, cmdline):
        assert cmdline.reproduce(Build())[0] == "tuxmake"

    def test_target_arch(self, cmdline):
        cmd = cmdline.reproduce(Build(target_arch="arm64"))
        assert "--target-arch=arm64" in cmd

    def test_runtime(self, cmdline):
        cmd = cmdline.reproduce(Build(runtime="docker"))
        assert "--runtime=docker" in cmd

    def test_image(self, mocker, cmdline):
        mocker.patch("tuxmake.runtime.DockerRuntime.get_image", return_value="myimage")
        cmd = cmdline.reproduce(Build(runtime="docker"))
        assert "--image=myimage" in cmd

    def test_targets(self, cmdline):
        cmd = cmdline.reproduce(Build(targets=["config", "kernel"]))
        assert cmd[-2:] == ["config", "kernel"]

    @pytest.mark.parametrize("option", ["jobs", "output-dir", "build-dir"])
    def test_ignore(self, cmdline, option):
        build = Build()
        cmd = cmdline.reproduce(build)
        opt = [o for o in cmd if o.startswith(f"--{option}")]
        assert opt == []

    def test_environment(self, cmdline):
        build = Build(environment={"FOO": "BAR"})
        cmd = cmdline.reproduce(build)
        assert "--environment=FOO=BAR" in cmd

    def test_kconfig_add(self, cmdline):
        build = Build(kconfig_add=["foo.config", "bar.config"])
        cmd = cmdline.reproduce(build)
        assert "--kconfig-add=foo.config" in cmd
        assert "--kconfig-add=bar.config" in cmd

    def test_debug(self, cmdline):
        cmd = cmdline.reproduce(Build(debug=True))
        assert "--debug" in cmd
