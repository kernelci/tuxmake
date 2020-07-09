import argparse
import pytest
import sys
from tuxmake.build import BuildInfo
from tuxmake.cli import main as tuxmake
from tuxmake.exceptions import TuxMakeException


@pytest.fixture
def builds(home):
    return home / ".cache/tuxmake/builds"


@pytest.fixture(autouse=True)
def builder(mocker):
    b = mocker.patch("tuxmake.cli.build")
    b.return_value.passed = True
    b.return_value.failed = False
    return b


def args(called):
    return argparse.Namespace(**called.call_args[1])


def test_basic_build(builder, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tuxmake"])
    tuxmake()
    assert builder.call_args[1] == {"tree": "."}


def test_basic_build_with_directory(linux, builder):
    tree = str(linux)
    tuxmake("--directory", tree)
    assert builder.call_args[1] == {"tree": tree}


def test_build_from_sys_argv(monkeypatch, builder):
    monkeypatch.setattr(sys, "argv", ["tuxmake", "--directory=/path/to/linux"])
    tuxmake()
    assert args(builder).tree == "/path/to/linux"


def test_build_from_sys_argv_default_tree_is_cwd(monkeypatch, builder):
    monkeypatch.setattr(sys, "argv", ["tuxmake"])
    tuxmake()
    assert args(builder).tree == "."


class TestTargets:
    def test_config(self, builder):
        tuxmake("config")
        args(builder).targets == ["config"]

    def test_config_multiple(self, builder):
        tuxmake("config", "kernel")
        assert args(builder).targets == ["config", "kernel"]


class TestKConfig:
    def test_kconfig(self, builder):
        tuxmake("--kconfig=olddefconfig")
        assert args(builder).kconfig == "olddefconfig"

    def test_kconfig_add(self, builder):
        tuxmake(
            "--kconfig-add=https://example.com/foo.config",
            "--kconfig-add=/path/to/local.config",
        )
        assert args(builder).kconfig_add == [
            "https://example.com/foo.config",
            "/path/to/local.config",
        ]


class TestToolchain:
    def test_toolchain(self, builder):
        tuxmake("--toolchain=gcc-10")
        assert args(builder).toolchain == "gcc-10"


class TestTargetArch:
    def test_target_arch(self, builder):
        tuxmake("--target-arch=arm64")
        assert args(builder).target_arch == "arm64"


class TestJobs:
    def test_jobs(self, builder):
        tuxmake("--jobs=300")
        assert args(builder).jobs == 300


class TestRuntime:
    def test_docker(self, builder):
        tuxmake("--runtime=docker")
        assert args(builder).runtime == "docker"


class TestVerbose:
    def test_verbose(self, builder):
        tuxmake("--verbose")
        assert args(builder).verbose


class TestExceptions:
    def test_basic(self, builder, capsys):
        builder.side_effect = TuxMakeException("hello")
        with pytest.raises(SystemExit) as exit:
            tuxmake("-C", "/path/to/linux")
        assert exit.value.code == 1
        _, err = capsys.readouterr()
        assert "E: hello" in err


class TestBuildStatus:
    def test_exits_2_on_build_failure(self, builder, capsys):
        builder.return_value.failed = True
        builder.return_value.status = {
            "config": BuildInfo("PASS", 1),
            "kernel": BuildInfo("FAIL", 2),
        }
        with pytest.raises(SystemExit) as exit:
            tuxmake("-C", "/path/to/linux")
        assert exit.value.code == 2

        _, err = capsys.readouterr()
        assert "config: PASS" in err
        assert "kernel: FAIL" in err
