import argparse
import os
from pathlib import Path
import pytest
import sys
from tuxmake.build import BuildInfo
from tuxmake.cli import main as tuxmake
from tuxmake.exceptions import TuxMakeException


@pytest.fixture
def builds(home):
    return home / ".cache/tuxmake/builds"


@pytest.fixture(autouse=True)
def builder(mocker, linux, tmp_path):
    b = mocker.patch("tuxmake.cli.Build")
    b.return_value.passed = True
    b.return_value.failed = False
    b.return_value.source_tree = linux
    b.return_value.output_dir = tmp_path
    return b


@pytest.fixture
def build(builder):
    return builder.return_value


def args(called):
    return argparse.Namespace(**called.call_args[1])


class TestBuildRun:
    def test_basic_build(self, build, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["tuxmake"])
        tuxmake()
        build.run.assert_called()


class TestTree:
    def test_basic_build(self, builder, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["tuxmake"])
        tuxmake()
        assert args(builder).tree == "."

    def test_basic_build_with_directory(self, linux, builder):
        tree = str(linux)
        tuxmake("--directory", tree)
        assert args(builder).tree == tree

    def test_build_from_sys_argv(self, monkeypatch, builder):
        monkeypatch.setattr(sys, "argv", ["tuxmake", "--directory=/path/to/linux"])
        tuxmake()
        assert args(builder).tree == "/path/to/linux"

    def test_build_from_sys_argv_default_tree_is_cwd(self, monkeypatch, builder):
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


class TestMakeVariables:
    def test_basic(self, builder):
        tuxmake("FOO=BAR")
        assert args(builder).make_variables == {"FOO": "BAR"}
        assert "targets" not in args(builder).__dict__

    def test_make_vars_and_targets(self, builder):
        tuxmake("FOO=BAR", "config")
        assert args(builder).make_variables == {"FOO": "BAR"}
        assert args(builder).targets == ["config"]

    def test_rejects_multiple_equal_signs(self, builder):
        with pytest.raises(SystemExit) as exit:
            tuxmake("FOO=BAR=QUX", "config")
        builder.assert_not_called()
        assert exit.value.code == 1


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


class TestImage:
    @pytest.fixture(autouse=True)
    def environment(self, monkeypatch):
        env = dict(os.environ)
        monkeypatch.setattr(os, "environ", env)
        return env

    def test_implies_runtime_docker(self, builder):
        tuxmake("--image=foobar")
        assert args(builder).runtime == "docker"

    def test_does_not_override_explicit_runtime(self, builder):
        tuxmake("--image=foobar", "--runtime=podman")
        assert args(builder).runtime == "podman"

    def test_not_passed_to_builder_class(self, builder):
        tuxmake("--image=foobar")
        assert "image" not in builder.call_args[1].keys()

    def test_sets_TUXMAKE_IMAGE(self, environment):
        tuxmake("--image=foobar")
        assert environment["TUXMAKE_IMAGE"] == "foobar"

    def test_backwards_compat_with_docker_image(self, environment, builder):
        tuxmake("--docker-image=foobar")
        assert environment["TUXMAKE_IMAGE"] == "foobar"
        assert "docker_image" not in builder.call_args[1].keys()


class TestImageRegistry:
    @pytest.fixture(autouse=True)
    def environment(self, monkeypatch):
        env = dict(os.environ)
        monkeypatch.setattr(os, "environ", env)
        return env

    def test_not_passed_to_builder_class(self, builder):
        tuxmake("--image-registry=localhost")
        assert "image_registry" not in builder.call_args[1].keys()

    def test_sets_env_variable(self, environment):
        tuxmake("--image-registry=localhost")
        assert environment["TUXMAKE_IMAGE_REGISTRY"] == "localhost"

    def test_implies_runtime_docker(self, builder):
        tuxmake("--image-registry=localhost")
        assert args(builder).runtime == "docker"

    def test_does_not_override_explicit_runtime(self, builder):
        tuxmake("--image-registry=localhost", "--runtime=podman")
        assert args(builder).runtime == "podman"


class TestFailFast:
    def test_fail_fast(self, builder):
        tuxmake("--fail-fast")
        assert args(builder).fail_fast


class TestVerbosity:
    def test_verbose(self, builder):
        tuxmake("--verbose")
        assert args(builder).verbose

    def test_quiet(self, builder):
        tuxmake("--quiet")
        assert args(builder).quiet

    def test_quiet_build(self, capsys):
        tuxmake("--quiet")
        out, err = capsys.readouterr()
        assert out == ""
        assert err == ""


class TestEnvironment:
    def test_environment(self, builder):
        tuxmake("--environment=FOO=BAR")
        assert args(builder).environment["FOO"] == "BAR"

    def test_multiple_environment_variables(self, builder):
        tuxmake("--environment=FOO=BAR", "--environment=BAZ=QUX")
        assert args(builder).environment["FOO"] == "BAR"
        assert args(builder).environment["BAZ"] == "QUX"

    def test_later_overrides_earlier(self, builder):
        tuxmake("--environment=FOO=BAR", "--environment=FOO=BAZ")
        assert args(builder).environment["FOO"] == "BAZ"

    def test_multiple_equal_signs(self, builder):
        tuxmake("--environment=OPTIONS=x=y")
        assert args(builder).environment["OPTIONS"] == "x=y"


class TestWrapper:
    def test_ccache(self, builder):
        tuxmake("--wrapper=ccache")
        assert args(builder).wrapper == "ccache"


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


class TestList:
    def test_list_architectures(self, builder, capsys):
        tuxmake("--list-architectures")
        builder.assert_not_called()
        out, _ = capsys.readouterr()
        assert "x86_64" in out
        assert "arm64" in out

    def test_list_toolchains(self, builder, capsys):
        tuxmake("--list-toolchains")
        builder.assert_not_called()
        out, _ = capsys.readouterr()
        assert "gcc" in out
        assert "clang" in out

    def test_list_docker_toolchains(self, builder, capsys):
        tuxmake("--runtime=docker", "--list-toolchains")
        builder.assert_not_called()
        out, _ = capsys.readouterr()
        assert "gcc" in out
        assert "gcc-10" in out
        assert "clang" in out
        assert "clang-10" in out

    def test_list_runtimes(self, builder, capsys):
        tuxmake("--list-runtimes")
        builder.assert_not_called()
        out, _ = capsys.readouterr()
        assert "null" in out
        assert "docker" in out


class TestPrintSupportMatrix:
    def test_print_support_matrix(self, builder, capsys):
        tuxmake("--print-support-matrix")
        builder.assert_not_called()
        out, _ = capsys.readouterr()
        assert out

    def test_print_support_matrix_docker(self, builder, capsys):
        tuxmake("--runtime=docker", "--print-support-matrix")
        builder.assert_not_called()
        out, _ = capsys.readouterr()
        assert "yes" in out
        assert "no" in out

    def test_output_colors_when_requested(self, builder, capsys):
        tuxmake("--runtime=docker", "--color=always", "--print-support-matrix")
        builder.assert_not_called()
        out, _ = capsys.readouterr()
        assert "\033" in out


class TestDebug:
    def test_shell(self, builder, mocker):
        run_cmd = builder.return_value.run_cmd
        tuxmake("--shell")
        run_cmd.assert_called_with(["bash"], interactive=True)

    def test_debug(self, builder, mocker):
        tuxmake("--debug")
        assert args(builder).debug


class TestOutputDir:
    def test_output_dir(self, builder):
        tuxmake("--output-dir=/path/to/output")
        assert args(builder).output_dir == Path("/path/to/output")

    def test_output_dir_relative_to_absolute(self, builder):
        cwd = Path.cwd()
        tuxmake("--output-dir=output")
        assert args(builder).output_dir == (cwd / "output")


class TestBuildDir:
    def test_build_dir(self, builder):
        tuxmake("--build-dir=/path/to/build")
        assert args(builder).build_dir == Path("/path/to/build")


class TestOptionsFromEnvironment:
    def test_options_from_environment(self, builder, monkeypatch):
        monkeypatch.setenv("TUXMAKE", "--debug --verbose")
        tuxmake("config")
        assert args(builder).debug
        assert args(builder).verbose

    def test_command_line_overrides_environment(self, builder, monkeypatch):
        monkeypatch.setenv("TUXMAKE", "--toolchain=gcc")
        tuxmake("--toolchain=clang")
        assert args(builder).toolchain == "clang"

    def test_command_line_plus_sys_argv(self, builder, monkeypatch):
        monkeypatch.setenv("TUXMAKE", "--toolchain=gcc")
        monkeypatch.setattr(sys, "argv", ["tuxmake", "--toolchain=clang"])
        tuxmake()
        assert args(builder).toolchain == "clang"


class TestConfigurationFiles:
    @pytest.fixture(autouse=True)
    def config_dir(self, home):
        confdir = home / ".config" / "tuxmake"
        confdir.mkdir(parents=True)
        return confdir

    def test_basics(self, builder, config_dir):
        with (config_dir / "ccache").open("w") as f:
            f.write("--wrapper=ccache\n")
        tuxmake("@ccache")
        assert args(builder).wrapper == "ccache"

    def test_default(self, builder, config_dir, monkeypatch):
        with (config_dir / "default").open("w") as f:
            f.write("--runtime=podman\n")
        monkeypatch.setattr(sys, "argv", [])
        tuxmake()
        assert args(builder).runtime == "podman"

    def test_escaping(self, builder, config_dir):
        with (config_dir / "escaping").open("w") as f:
            f.write("--environment=FOO='bar baz'\n")
        tuxmake("@escaping")
        assert args(builder).environment["FOO"] == "bar baz"

    def test_order(self, builder, config_dir):
        with (config_dir / "before").open("w") as f:
            f.write("--runtime=podman\n")
        with (config_dir / "after").open("w") as f:
            f.write("--kconfig=defconfig\n")
        tuxmake("@before", "--runtime=null", "--kconfig=tinyconfig", "@after")
        assert args(builder).runtime == "null"
        assert args(builder).kconfig == "defconfig"

    def test_comments(self, builder, config_dir):
        with (config_dir / "comments").open("w") as f:
            f.write("# this is a comment\n")
        tuxmake("@comments")
        assert "targets" not in args(builder)

    def test_missing_config_file(self, capsys):
        with pytest.raises(SystemExit) as exit:
            tuxmake("@missing")
        _, err = capsys.readouterr()

        assert exit.value.code == 1
        assert "E: missing configuration file: " in err

    def test_absolute_path(self, builder, home):
        with (home / "file").open("w") as f:
            f.write("--environment=FOO=BAR\n")
        tuxmake(f"@{home}/file")
        assert args(builder).environment["FOO"] == "BAR"

    def test_XDG_CONFIG_HOME(self, builder, home, monkeypatch):
        custom_config_dir = home / "customconfig"
        (custom_config_dir / "tuxmake").mkdir(parents=True)
        with (custom_config_dir / "tuxmake" / "myconfig").open("w") as f:
            f.write("--environment=CONFIG=custom")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(custom_config_dir))
        tuxmake("@myconfig")
        assert args(builder).environment["CONFIG"] == "custom"


class TestKernel:
    def test_kernel(self, builder):
        tuxmake("--kernel-image=Image.bz2")
        assert args(builder).kernel_image == "Image.bz2"


@pytest.fixture
def check_call(mocker):
    return mocker.patch("subprocess.check_call")


class TestHooks:
    def test_pre_build_hook(self, check_call, linux):
        tuxmake('--pre-build-hook=echo "hello world"')
        check_call.assert_called_with(
            ["sh", "-c", 'echo "hello world"'], cwd=str(linux)
        )

    def test_failed_pre_build_hook_stops_build(self, build, linux):
        with pytest.raises(SystemExit):
            tuxmake("--pre-build-hook=false")
        build.run.assert_not_called()

    def test_post_build_hook(self, check_call, linux):
        tuxmake("--post-build-hook=git clean -dxf")
        check_call.assert_called_with(["sh", "-c", "git clean -dxf"], cwd=str(linux))

    def test_post_build_hook_failure_means_exit_failure(self):
        with pytest.raises(SystemExit) as exit:
            tuxmake("--post-build-hook=false")
        assert exit.value.code == 2

    def test_post_build__hook_does_not_run_if_build_failed(self, build, check_call):
        build.passed = False
        build.failed = True
        with pytest.raises(SystemExit) as exit:
            tuxmake("--post-build-hook=true")
        assert exit.value.code == 2
        check_call.assert_not_called()

    def test_results_hook(self, check_call, tmp_path):
        tuxmake("--results-hook=ls -1")
        check_call.assert_called_with(["sh", "-c", "ls -1"], cwd=str(tmp_path))

    def test_results_hook_failure_means_exit_failure(self):
        with pytest.raises(SystemExit) as exit:
            tuxmake("--results-hook=false")
        assert exit.value.code == 2

    def test_results_hook_does_not_run_if_build_failed(self, build, check_call):
        build.passed = False
        build.failed = True
        with pytest.raises(SystemExit):
            tuxmake("--results-hook=true")
        check_call.assert_not_called()


class TestCheckEnvironment:
    def test_check_environment(self, build):
        tuxmake("--check-environment")
        build.check_environment.assert_called()
        build.run.assert_not_called()


class TestKorgGccDownloadAll:
    def test_download_all_korg_gcc_toolchains(self, build):
        tuxmake("--download-all-korg-gcc-toolchains")
        build.download_all_korg_gcc_toolchains.assert_called()
        build.run.assert_not_called()
