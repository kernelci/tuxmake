from io import StringIO
import sys
import pytest
import tuxmake.cmdline
from tuxmake.cmdline import CommandLine
from tuxmake.cmdline import BashCompletion
from tuxmake.cmdline import main
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
        assert cmd[-1] == "kernel"

    def test_make_variables(self, cmdline):
        cmd = cmdline.reproduce(
            Build(targets=["config"], make_variables={"FOO": "BAR"})
        )
        assert cmd[-2:] == ["FOO=BAR", "config"]

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


class TestBashCompletion:
    def test_basic(self):
        stream = StringIO()
        completion = BashCompletion()
        completion.emit(stream)
        output = stream.getvalue()
        assert "complete -o bashdefault -o default -F _tuxmake tuxmake" in output

    def test_main(self, monkeypatch, mocker):
        emit = mocker.patch("tuxmake.cmdline.BashCompletion.emit")
        monkeypatch.setattr(tuxmake.cmdline, "__name__", "__main__")
        monkeypatch.setattr(sys, "argv", ["", "bash_completion"])
        main()
        emit.assert_called()
