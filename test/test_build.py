import json
from pathlib import Path
import os
import pytest
import re
import subprocess
import shutil
import urllib
from tuxmake.arch import Architecture, Native
from tuxmake.toolchain import Toolchain
from tuxmake.build import build
from tuxmake.build import Build
from tuxmake.build import BuildInfo
from tuxmake.build import defaults
from tuxmake.build import Terminated
from tuxmake.build import get_image
from tuxmake.build import DEFAULT_CONTAINER_REGISTRY
from tuxmake.target import Command
from tuxmake.target import default_compression
import tuxmake.exceptions


@pytest.fixture
def kernel():
    return Native().targets["kernel"]


@pytest.fixture
def output_dir(tmp_path):
    out = tmp_path / "output"
    return out


@pytest.fixture
def check_artifacts(mocker):
    return mocker.patch("tuxmake.build.Build.check_artifacts", return_value=True)


# Disable the metadata extraction for non-metadata related tests since its
# pretty slow.
@pytest.fixture(autouse=True)
def collect_metadata(mocker):
    return mocker.patch("tuxmake.build.Build.collect_metadata")


@pytest.fixture
def run_cmd(mocker):
    rcmd = mocker.patch("tuxmake.build.Build.run_cmd")
    rcmd.return_value.returncode = 0
    return rcmd


def args(called):
    return called.call_args[0][0]


def kwargs(called):
    return called.call_args[1]


class TestBasicFunctionality:
    def test_invalid_directory(self, tmp_path):
        (tmp_path / "Makefile").touch()
        with pytest.raises(tuxmake.exceptions.UnrecognizedSourceTree):
            build(tree=tmp_path)

    def test_build(self, linux, home, kernel):
        result = build(tree=linux)
        assert kernel in result.artifacts["kernel"]
        assert (home / ".cache/tuxmake/builds/1" / kernel).exists()
        assert result.passed

    def test_build_with_output_dir(self, linux, output_dir, kernel):
        result = build(tree=linux, output_dir=output_dir)
        assert kernel in result.artifacts["kernel"]
        assert (output_dir / kernel).exists()
        assert result.output_dir == output_dir

    def test_build_with_build_dir(self, linux, tmp_path):
        build(tree=linux, build_dir=tmp_path)
        assert (tmp_path / ".config").exists

    def test_no_directory_created_unecessarily(self, linux, home):
        Build(tree=linux)
        assert len(list(home.glob("*"))) == 0

    def test_no_directory_created_unecessarily_with_explicit_paths(
        self, linux, tmp_path
    ):
        Build(tree=linux, output_dir=tmp_path / "output", build_dir=tmp_path / "build")
        assert not (tmp_path / "output").exists()
        assert not (tmp_path / "build").exists()

    def test_unsupported_target(self, linux):
        with pytest.raises(tuxmake.exceptions.UnsupportedTarget):
            build(tree=linux, targets=["unknown-target"])


class TestKconfig:
    def test_kconfig_default(self, linux, Popen):
        b = Build(tree=linux, targets=["config"])
        b.build(b.targets[0])
        assert "defconfig" in args(Popen)

    def test_kconfig_named(self, linux, Popen):
        b = Build(tree=linux, targets=["config"], kconfig="fooconfig")
        b.build(b.targets[0])
        assert "fooconfig" in args(Popen)

    def test_kconfig_named_invalid(self, linux, mocker):
        with pytest.raises(tuxmake.exceptions.UnsupportedKconfig):
            build(tree=linux, targets=["config"], kconfig="foobar")

    def test_kconfig_url(self, linux, mocker, output_dir):
        response = mocker.MagicMock()
        response.getcode.return_value = 200
        response.read.return_value = b"CONFIG_FOO=y\nCONFIG_BAR=y\n"
        mocker.patch("urllib.request.urlopen", return_value=response)

        build(
            tree=linux,
            targets=["config"],
            kconfig="https://example.com/config.txt",
            output_dir=output_dir,
        )
        config = output_dir / "config"
        assert "CONFIG_FOO=y\nCONFIG_BAR=y\n" in config.read_text()

    def test_kconfig_url_not_found(self, linux, mocker):
        mocker.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                "https://example.com/config.txt", 404, "Not Found", {}, None
            ),
        )

        with pytest.raises(tuxmake.exceptions.InvalidKConfig):
            build(
                tree=linux, targets=["config"], kconfig="https://example.com/config.txt"
            )

    def test_kconfig_localfile(self, linux, tmp_path, output_dir):
        extra_config = tmp_path / "extra_config"
        extra_config.write_text("CONFIG_XYZ=y\nCONFIG_ABC=m\n")
        build(
            tree=linux,
            targets=["config"],
            kconfig=str(extra_config),
            output_dir=output_dir,
        )
        config = output_dir / "config"
        assert "CONFIG_XYZ=y\nCONFIG_ABC=m\n" in config.read_text()

    def test_kconfig_add_url(self, linux, mocker, output_dir):
        response = mocker.MagicMock()
        response.getcode.return_value = 200
        response.read.return_value = b"CONFIG_FOO=y\nCONFIG_BAR=y\n"
        mocker.patch("urllib.request.urlopen", return_value=response)

        build(
            tree=linux,
            targets=["config"],
            kconfig="defconfig",
            kconfig_add=["https://example.com/config.txt"],
            output_dir=output_dir,
        )
        config = output_dir / "config"
        assert "CONFIG_FOO=y\nCONFIG_BAR=y\n" in config.read_text()

    def test_kconfig_add_localfile(self, linux, tmp_path, output_dir):
        extra_config = tmp_path / "extra_config"
        extra_config.write_text("CONFIG_XYZ=y\nCONFIG_ABC=m\n")
        build(
            tree=linux,
            targets=["config"],
            kconfig_add=[str(extra_config)],
            output_dir=output_dir,
        )
        config = output_dir / "config"
        assert "CONFIG_XYZ=y\nCONFIG_ABC=m\n" in config.read_text()

    def test_kconfig_add_inline(self, linux, output_dir):
        build(
            tree=linux,
            targets=["config"],
            kconfig_add=["CONFIG_FOO=y"],
            output_dir=output_dir,
        )
        config = output_dir / "config"
        assert "CONFIG_FOO=y\n" in config.read_text()

    def test_kconfig_add_inline_not_set(self, linux, output_dir):
        build(
            tree=linux,
            targets=["config"],
            kconfig_add=["# CONFIG_FOO is not set"],
            output_dir=output_dir,
        )
        config = output_dir / "config"
        assert "CONFIG_FOO is not set\n" in config.read_text()

    def test_kconfig_add_inline_set_to_no(self, linux, output_dir):
        build(
            tree=linux,
            targets=["config"],
            kconfig_add=["CONFIG_FOO=n"],
            output_dir=output_dir,
        )
        config = output_dir / "config"
        assert "CONFIG_FOO=n\n" in config.read_text()

    def test_kconfig_add_in_tree(self, linux, output_dir):
        build(
            tree=linux,
            targets=["config"],
            kconfig_add=["kvm_guest.config", "qemu-gdb.config"],
            output_dir=output_dir,
        )
        config = output_dir / "config"
        assert ("CONFIG_KVM_GUEST=y") in config.read_text()
        assert ("CONFIG_DEBUG_INFO=y") in config.read_text()

    def test_kconfig_add_explicit_make_target(self, linux, output_dir):
        build(
            tree=linux,
            targets=["config"],
            kconfig_add=["make:kselftest-merge"],
            output_dir=output_dir,
        )
        config = output_dir / "config"
        assert "CONFIG_KSELFTEST_MERGE=y" in config.read_text()

    def test_kconfig_add_explicit_interactive_make_target(self, linux, Popen):
        build = Build(
            tree=linux,
            targets=["config"],
            kconfig_add=["imake:menuconfig"],
        )
        build.build(build.targets[0])
        cmd = build.targets[-1].commands[1]
        assert cmd == ["{make}", "menuconfig"]
        assert cmd.interactive

    def test_kconfig_add_invalid(self, linux):
        with pytest.raises(tuxmake.exceptions.UnsupportedKconfigFragment):
            build(tree=linux, targets=["config"], kconfig_add=["foo"])

    def test_kconfig_from_source_tree(self, linux):
        b = build(tree=linux, targets=["config"], kconfig="config/test.config")
        config = b.output_dir / "config"
        assert "CONFIG_IN_SOURCE_CONFIG_FILE=y" in config.read_text()


def test_output_dir(linux, output_dir, kernel):
    build(tree=linux, output_dir=output_dir)
    artifacts = [str(f.name) for f in output_dir.glob("*")]
    assert "config" in artifacts
    assert kernel in artifacts
    assert "arch" not in artifacts


def test_copies_artifacts_from_failed_targets(linux, output_dir, mocker):
    mocker.patch("tuxmake.build.Build.check_artifacts", return_value=False)
    build(tree=linux, output_dir=output_dir, targets=["config"])
    artifacts = [str(f.name) for f in output_dir.glob("*")]
    assert "config" in artifacts


def test_saves_log(linux):
    result = build(tree=linux)
    artifacts = [str(f.name) for f in result.output_dir.glob("*")]
    assert "build.log" in result.artifacts["log"]
    assert "build.log" in artifacts
    log = result.output_dir / "build.log"
    assert "make --silent" in log.read_text()


def test_timestamp_in_debug_log(linux):
    result = build(tree=linux)
    log = result.output_dir / "build-debug.log"
    assert "00:00" in log.read_text()


def test_build_failure(linux, kernel, monkeypatch):
    monkeypatch.setenv("FAIL", "kernel")
    result = build(tree=linux, targets=["config", "kernel"])
    assert not result.passed
    assert result.failed
    artifacts = [str(f.name) for f in result.output_dir.glob("*")]
    assert "build.log" in artifacts
    assert "config" in artifacts
    assert kernel not in artifacts


def test_concurrency_default(linux, Popen):
    b = Build(tree=linux, targets=["config"])
    b.build(b.targets[0])
    assert f"--jobs={defaults.jobs}" in args(Popen)


def test_concurrency_set(linux, Popen):
    b = Build(tree=linux, targets=["config"], jobs=99)
    b.build(b.targets[0])
    assert "--jobs=99" in args(Popen)


def test_fail_fast(linux, mocker, Popen):
    b = Build(tree=linux, targets=["config"], fail_fast=True)
    b.build(b.targets[0])
    assert "--keep-going" not in args(Popen)


def test_fail_fast_aborts_build(linux, monkeypatch):
    """
    `dtbs` do not depend on `kernel`; normally, `dtbs` will still be built even
    if the kernel build fails. When fail_fast is set, though, the build stops
    after the first target fails, regardless of dependencies.
    """
    b = Build(tree=linux, fail_fast=True, target_arch="arm64")
    monkeypatch.setenv("FAIL", "kernel")
    b.run()
    assert b.status["default"].failed
    assert b.status["dtbs"].skipped


def test_verbose(linux, mocker, Popen):
    b = Build(tree=linux, targets=["config"], verbose=True)
    b.build(b.targets[0])
    assert "--silent" not in args(Popen)


def test_default_targets(linux):
    b = Build(tree=linux, targets=[])
    assert set(t.name for t in b.targets) == set(defaults.targets) | set(["default"])


def test_quiet(linux, capfd):
    build(tree=linux, quiet=True)
    out, err = capfd.readouterr()
    assert out == ""
    assert "I:" not in err


class TestInterruptedBuild:
    @pytest.fixture
    def interrupted(self, mocker, Popen):
        process = mocker.MagicMock()
        Popen.return_value = process
        process.wait.side_effect = KeyboardInterrupt()
        return process

    def test_ctrl_c(self, linux, interrupted):
        b = Build(tree=linux)
        res = b.build(b.targets[0])
        interrupted.terminate.assert_called()
        assert res.failed
        assert b.interrupted

    def test_ctrl_c_skips_all_other_targets(self, linux, interrupted, mocker):
        b = Build(tree=linux)
        real_build = b.build
        mock_build = mocker.patch("tuxmake.build.Build.build", wraps=real_build)
        b.build_all_targets()
        expected_statuses = ["FAIL"] + ["SKIP" for _ in b.targets[1:]]
        statuses = [b.status[t.name].status for t in b.targets]
        assert statuses == expected_statuses
        assert mock_build.call_count == 1

    def test_always_run_cleanup(self, linux, mocker):
        build = Build(tree=linux)
        mocker.patch(
            "tuxmake.build.Build.build_all_targets", side_effect=KeyboardInterrupt()
        )
        with pytest.raises(KeyboardInterrupt):
            build.run()
        assert not build.build_dir.exists()

    def test_cleans_up_even_if_prepare_fails(self, linux, mocker):
        build = Build(tree=linux)
        mocker.patch("tuxmake.build.Build.prepare", side_effect=KeyboardInterrupt())
        with pytest.raises(KeyboardInterrupt):
            build.run()
        assert not build.build_dir.exists()

    def test_copies_artifacts_even_when_interrupted(self, linux, mocker):
        build = Build(tree=linux)
        mocker.patch(
            "tuxmake.build.Build.build_all_targets", side_effect=KeyboardInterrupt()
        )
        copy_artifacts = mocker.patch("tuxmake.build.Build.copy_artifacts")
        with pytest.raises(KeyboardInterrupt):
            build.run()
        assert copy_artifacts.call_count > 0

    def test_gets_metadata_even_when_interrupted(self, linux, mocker, collect_metadata):
        build = Build(tree=linux)
        mocker.patch(
            "tuxmake.build.Build.build_all_targets", side_effect=KeyboardInterrupt()
        )
        with pytest.raises(KeyboardInterrupt):
            build.run()
        assert collect_metadata.call_count == 1
        assert (build.output_dir / "metadata.json").exists()

    def test_does_not_collect_metadata_when_runtime_preparation_fails(
        self, linux, mocker, collect_metadata
    ):
        build = Build(tree=linux)
        mocker.patch(
            "tuxmake.runtime.NullRuntime.prepare",
            side_effect=RuntimeError("PREPARE FAILED"),
        )
        with pytest.raises(RuntimeError):
            build.run()
        assert collect_metadata.call_count == 0


clang_version = int(
    subprocess.check_output(["clang", "-dumpversion"], encoding="utf-8").split(".")[0]
)


class TestArchitecture:
    def test_x86_64(self, linux):
        result = build(tree=linux, target_arch="x86_64")
        assert "bzImage" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_arm64(self, linux):
        result = build(tree=linux, target_arch="arm64")
        assert "Image.gz" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_arm(self, linux):
        result = build(tree=linux, target_arch="arm")
        assert "zImage" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_i386(self, linux):
        result = build(tree=linux, target_arch="i386")
        assert "bzImage" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_mips(self, linux):
        result = build(tree=linux, target_arch="mips")
        assert "uImage.gz" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_parisc(self, linux):
        result = build(tree=linux, target_arch="parisc")
        assert "bzImage" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_powerpc(self, linux):
        result = build(tree=linux, target_arch="powerpc")
        assert "zImage" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_riscv(self, linux):
        result = build(tree=linux, target_arch="riscv")
        assert "Image.gz" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_s390(self, linux):
        result = build(tree=linux, target_arch="s390")
        assert "bzImage" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_sh(self, linux):
        result = build(tree=linux, target_arch="sh")
        assert "zImage" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_sparc(self, linux):
        result = build(tree=linux, target_arch="sparc")
        assert "zImage" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_arc(self, linux):
        result = build(tree=linux, target_arch="arc")
        assert "uImage.gz" in [str(f.name) for f in result.output_dir.glob("*")]

    @pytest.mark.skipif(shutil.which("ld.lld") is None, reason="requires lld")
    @pytest.mark.skipif(clang_version < 10, reason="requires clang 10+")
    def test_hexagon(self, linux):
        result = build(tree=linux, target_arch="hexagon", toolchain="clang")
        assert result.passed
        assert "vmlinux" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_invalid_arch(self):
        with pytest.raises(tuxmake.exceptions.UnsupportedArchitecture):
            Architecture("foobar")


class TestToolchain:
    # Test that the right make arguments are passed, when needed. Ideally we
    # would want more black box tests that check the results of the build, but
    # for that we would need a reliable mechanism to check which toolchain was
    # used to build a given binary.
    def test_gcc_10(self, linux, Popen):
        b = Build(tree=linux, targets=["config"], toolchain="gcc-10")
        b.build(b.targets[0])
        cmdline = args(Popen)
        assert all(["CC=" not in arg for arg in cmdline])

    def test_gcc_10_cross(self, linux, Popen):
        b = Build(
            tree=linux, targets=["config"], toolchain="gcc-10", target_arch="arm64"
        )
        b.build(b.targets[0])
        cmdline = args(Popen)
        assert all(["CC=" not in arg for arg in cmdline])
        assert "CROSS_COMPILE=aarch64-linux-gnu-" in cmdline

    def test_korg_gcc_14(self, linux, Popen):
        b = Build(tree=linux, targets=["config"], toolchain="korg-gcc-14")
        b.prepare()
        assert b.prepare_korg_gcc is True
        b.build(b.targets[0])
        cmdline = args(Popen)
        assert "HOSTCC=gcc" in cmdline

    def test_korg_gcc_14_cross(self, linux, Popen):
        b = Build(
            tree=linux,
            targets=["config"],
            toolchain="korg-gcc-14",
            target_arch="arm64",
            runtime="docker",
        )
        b.build(b.targets[0])
        cmdline = args(Popen)
        assert "HOSTCC=gcc" in cmdline
        assert "CROSS_COMPILE=aarch64-linux-gnu-" in cmdline

    def test_clang(self, linux, Popen):
        b = Build(tree=linux, targets=["config"], toolchain="clang")
        b.build(b.targets[0])
        cmdline = args(Popen)
        assert "CC=clang" in cmdline

    def test_invalid_toolchain(self):
        with pytest.raises(tuxmake.exceptions.UnsupportedToolchain):
            Toolchain("foocc")

    def test_prepare_warns_about_versioned_toolchain(self, linux, mocker):
        build = Build(tree=linux, toolchain="gcc-10", runtime="null")
        log = mocker.patch("tuxmake.build.Build.log")
        build.prepare()
        log.assert_called()
        assert "versioned toolchains" in log.call_args[0][0]


class TestDebugKernel:
    def test_build_with_debugkernel(self, linux):
        result = build(tree=linux, targets=["config", "debugkernel"])
        artifacts = [str(f.name) for f in result.output_dir.glob("*")]
        assert "vmlinux.xz" in artifacts
        assert "System.map" in artifacts

    def test_build_with_debugkernel_arm64(self, linux):
        result = build(
            tree=linux, targets=["config", "debugkernel"], target_arch="arm64"
        )
        artifacts = [str(f.name) for f in result.output_dir.glob("*")]
        assert "vmlinux.xz" in artifacts
        assert "System.map" in artifacts

    def test_reuse_build_directory(self, linux, tmp_path):
        build(tree=linux, targets=["config", "debugkernel"], build_dir=tmp_path)
        r = build(tree=linux, targets=["config", "debugkernel"], build_dir=tmp_path)
        assert r.passed


class TestRunCmd:
    def test_pass(self, linux):
        build = Build(tree=linux)
        assert build.run_cmd(["true"])

    def test_fail(self, linux):
        build = Build(tree=linux)
        assert not build.run_cmd(["false"])

    def test_negate(self, linux):
        build = Build(tree=linux)
        assert build.run_cmd(["!", "false"])


class TestXIPKernel:
    def test_xip_kernel(self, linux):
        result = build(tree=linux, kconfig_add=["CONFIG_XIP_KERNEL=y"])
        assert result.passed
        artifacts = [str(f.name) for f in result.output_dir.glob("*")]
        assert "xipImage" in artifacts


class TestModules:
    def test_modules(self, linux):
        result = build(tree=linux, targets=["config", "kernel", "modules"])
        artifacts = [str(f.name) for f in result.output_dir.glob("*")]
        assert "modules.tar.xz" in artifacts

    def test_skip_if_not_configured_for_modules(self, linux):
        result = build(
            tree=linux, targets=["config", "kernel", "modules"], kconfig="tinyconfig"
        )
        artifacts = [str(f.name) for f in result.output_dir.glob("*")]
        assert "modules.tar.xz" not in artifacts

    def test_cleans_up_modules_install_directory(self, tmp_path, linux_rw):
        build_dir = tmp_path / "build"
        build(tree=linux_rw, build_dir=build_dir, targets=["modules"])
        makefile = str(linux_rw / "Makefile")
        subprocess.check_call(
            ["sed", "-i", "-e", "s/^VERSION.*/VERSION = 9.9.9.9.9/", makefile]
        )
        b = build(tree=linux_rw, build_dir=build_dir, targets=["modules"])
        tarball = b.output_dir / "modules.tar.xz"
        items = subprocess.check_output(
            ["tar", "taf", str(tarball)], encoding="utf-8"
        ).split("\n")
        modules = [i for i in items if i.endswith("/ext4.ko")]
        assert modules == ["lib/modules/9.9.9.9.9/kernel/fs/ext4/ext4.ko"]


def tarball_contents(tarball):
    return subprocess.check_output(["tar", "taf", tarball]).decode("utf-8").splitlines()


class TestDtbs:
    def test_dtbs(self, linux):
        result = build(tree=linux, target_arch="arm64")
        artifacts = [str(f.name) for f in result.output_dir.glob("*")]
        assert result.status["dtbs"].status == "PASS"
        assert "dtbs/hisilicon/hi6220-hikey.dtb" in tarball_contents(
            result.output_dir / "dtbs.tar.xz"
        )
        assert "dtbs.tar.xz" in artifacts

    def test_relative_path_to_source_tree(self, linux):
        cwd = Path.cwd()
        try:
            os.chdir(Path(linux).parent)
            result = build(tree="linux", target_arch="arm64")
            assert result.status["dtbs"].status == "PASS"
            assert "dtbs/hisilicon/hi6220-hikey.dtb" in tarball_contents(
                result.output_dir / "dtbs.tar.xz"
            )
            artifacts = [str(f.name) for f in result.output_dir.glob("*")]
            assert "dtbs.tar.xz" in artifacts
        finally:
            os.chdir(cwd)

    def test_skip_on_arch_with_no_dtbs(self, linux):
        result = build(tree=linux, target_arch="x86_64")
        artifacts = [str(f.name) for f in result.output_dir.glob("*")]
        assert "dtbs.tar.xz" not in artifacts


class TestDtbsLegacy:
    @pytest.fixture
    def oldlinux(self, linux_rw, tmp_path):
        subprocess.check_call(
            ["sed", "-i", "-e", "s/dtbs_install/XXXX/g", str(linux_rw / "Makefile")]
        )
        with (linux_rw / "arch/arm64/Makefile").open("a") as f:
            f.write("\n\ndtbs:\n\t@echo build dtbs\n")
        return linux_rw

    def test_collect_dtbs_manually_without_dtbs_install(self, oldlinux):
        result = build(tree=oldlinux, target_arch="arm64")
        artifacts = [str(f.name) for f in result.output_dir.glob("*")]
        assert "dtbs.tar.xz" in artifacts
        assert result.status["dtbs-legacy"].status == "PASS"
        errors, _ = result.parse_log()
        assert errors == 0
        assert "dtbs/hisilicon/hi6220-hikey.dtb" in tarball_contents(
            result.output_dir / "dtbs.tar.xz"
        )

    def test_collect_dtbs_manually_without_dtbs_install_and_fails(
        self, oldlinux, monkeypatch
    ):
        build = Build(tree=oldlinux, target_arch="arm64")
        dtbs_legacy = [t for t in build.targets if t.name == "dtbs-legacy"][0]
        monkeypatch.setattr(dtbs_legacy, "commands", [Command(["false"])])
        build.run()
        assert build.failed


class TestTargetDependencies:
    def test_dont_build_kernel_if_config_fails(self, linux, monkeypatch):
        monkeypatch.setenv("FAIL", "defconfig")
        result = build(tree=linux)
        assert result.status["config"].failed
        assert result.status["kernel"].skipped

    def test_include_dependencies_in_targets(self, linux):
        result = build(tree=linux, targets=["kernel"])
        assert result.status["config"].passed
        assert result.status["kernel"].passed

    def test_recursive_dependencies(self, linux):
        result = build(tree=linux, targets=["kernel"])
        assert result.status["default"].passed
        assert result.status["config"].passed


class TestRuntime:
    def test_null(self, linux):
        build = Build(tree=linux)
        assert build.runtime

    def test_docker(self, linux):
        build = Build(tree=linux, runtime="docker")
        assert build.runtime

    def test_interactive_command(self, linux, mocker):
        runtime = mocker.patch("tuxmake.runtime.Runtime.get").return_value
        runtime.get_command_line.return_value = ["true"]
        build = Build(tree=linux, runtime="docker")
        build.run_cmd(["true"], interactive=True)
        assert kwargs(runtime.run_cmd)["interactive"]


class TestEnvironment:
    def test_basics(self, linux, Popen):
        b = Build(
            tree=linux,
            environment={"KCONFIG_ALLCONFIG": "foo.config"},
            targets=["config"],
        )
        b.prepare()
        assert b.runtime.environment["KCONFIG_ALLCONFIG"] == "foo.config"


class TestMakeVariables:
    def test_basics(self, linux, Popen):
        b = Build(tree=linux, make_variables={"LLVM": "1"}, targets=["config"])
        b.build(b.targets[0])
        assert "LLVM=1" in args(Popen)

    def test_reject_make_variables_set_by_us(self, linux):
        with pytest.raises(tuxmake.exceptions.UnsupportedMakeVariable):
            Build(make_variables={"O": "/path/to/build"})


class TestCompilerWrappers:
    def test_ccache(self, linux, Popen):
        b = Build(tree=linux, targets=["config"], wrapper="ccache")
        b.prepare()
        assert "CCACHE_DIR" in b.runtime.environment
        makevars = b.makevars
        assert makevars["CC"] == "ccache gcc"
        assert makevars["HOSTCC"] == "ccache gcc"

    def test_ccache_with_container_runtime(self, linux, Popen, mocker):
        b = Build(tree=linux, targets=["config"], wrapper="ccache", runtime="podman")
        mocker.patch("tuxmake.runtime.ContainerRuntime.prepare")
        mocker.patch("tuxmake.wrapper.Wrapper.prepare_runtime")
        b.prepare()
        cache_dir = b.wrapper.environment["CCACHE_DIR"]
        assert (cache_dir, cache_dir, False, False) in b.runtime.volumes

    def test_ccache_gcc_v(self, linux, Popen):
        b = Build(tree=linux, targets=["config"], toolchain="gcc-10", wrapper="ccache")
        b.build(b.targets[0])
        assert "CC=ccache gcc" in args(Popen)
        assert "HOSTCC=ccache gcc" in args(Popen)

    def test_ccache_target_arch(self, linux, Popen):
        b = Build(tree=linux, targets=["config"], target_arch="arm64", wrapper="ccache")
        b.build(b.targets[0])
        assert "CC=ccache aarch64-linux-gnu-gcc" in args(Popen)

    def test_ccache_target_arch_and_gcc_v(self, linux, Popen):
        b = Build(
            tree=linux,
            targets=["config"],
            toolchain="gcc-10",
            target_arch="arm64",
            wrapper="ccache",
        )
        b.build(b.targets[0])
        assert "CC=ccache aarch64-linux-gnu-gcc" in args(Popen)

    def test_ccache_llvm(self, linux, Popen):
        b = Build(
            tree=linux,
            targets=["config"],
            toolchain="llvm",
            target_arch="arm64",
            wrapper="ccache",
        )
        b.build(b.targets[0])
        assert "CC=ccache clang" in args(Popen)

    def test_ccache_llvm_dir(self, linux, Popen):
        b = Build(
            make_variables={"LLVM": "/foo/bar/bin/"},
            tree=linux,
            targets=["config"],
            toolchain="llvm",
            target_arch="arm64",
            wrapper="ccache",
        )
        b.build(b.targets[0])
        assert "CC=ccache /foo/bar/bin/clang" in args(Popen)

    def test_ccache_llvm_ver(self, linux, Popen):
        b = Build(
            make_variables={"LLVM": "-15"},
            tree=linux,
            targets=["config"],
            toolchain="llvm",
            target_arch="arm64",
            wrapper="ccache",
        )
        b.build(b.targets[0])
        assert "CC=ccache clang-15" in args(Popen)

    def test_sccache_with_path(self, linux, mocker, Popen):
        add_volume = mocker.patch("tuxmake.runtime.Runtime.add_volume")
        b = Build(tree=linux, wrapper="/path/to/sccache")
        b.prepare()
        volumes = [call[0] for call in add_volume.call_args_list]
        assert ("/path/to/sccache", "/usr/local/bin/sccache") in volumes


@pytest.mark.skipif(
    [int(n) for n in pytest.__version__.split(".")] < [3, 10], reason="old pytest"
)
class TestMetadata:
    @pytest.fixture(scope="class")
    def build(self, linux):
        build = Build(tree=linux, environment={"WARN": "kernel", "FAIL": "modules"})
        build.run()
        return build

    @pytest.fixture(scope="class")
    def metadata(self, build):
        return json.loads((build.output_dir / "metadata.json").read_text())

    def test_kernelversion(self, metadata):
        assert (
            re.match(r"^[0-9]+\.[0-9]+", metadata["source"]["kernelversion"])
            is not None
        )

    def test_kernelrelease(self, metadata):
        assert metadata["source"]["kernelrelease"].startswith(
            metadata["source"]["kernelversion"]
        )

    def test_metadata_file(self, metadata):
        assert type(metadata) is dict

    def test_build_metadata(self, metadata):
        assert type(metadata["build"]) is dict

    def test_status(self, metadata):
        assert metadata["results"]["status"] == "FAIL"

    @pytest.mark.parametrize(
        "stage", ["validate", "prepare", "build", "copy", "metadata", "cleanup"]
    )
    def test_duration(self, metadata, stage):
        assert metadata["results"]["duration"][stage] > 0.0

    def test_targets(self, metadata):
        assert metadata["results"]["targets"]["kernel"]["status"] == "PASS"
        assert metadata["results"]["targets"]["kernel"]["duration"] > 0.0

    def test_command_line(self, metadata):
        assert type(metadata["build"]["reproducer_cmdline"]) is list


class TestParseLog:
    @pytest.fixture(scope="class")
    def build(self, linux, logs_directory):
        b = Build(tree=linux)
        log = (logs_directory / "simple.log").read_text()
        (b.output_dir / "build.log").write_text(log)
        return b

    def test_warnings(self, build):
        _, warnings = build.parse_log()
        assert warnings == 1

    def test_errors(self, build):
        errors, _ = build.parse_log()
        assert errors == 1


class TestUnsupportedToolchainArchitectureCombination:
    def test_exception(self, linux, mocker):
        mocker.patch("tuxmake.runtime.Runtime.is_supported", return_value=False)
        with pytest.raises(
            tuxmake.exceptions.UnsupportedArchitectureToolchainCombination
        ):
            Build(tree=linux, target_arch="arc", toolchain="clang")


class TestDebug:
    def test_no_debug_without_debug_options(self, linux, capfd):
        build = Build(tree=linux)
        build.run_cmd(["true"])
        _, e = capfd.readouterr()
        assert e == ""

    @pytest.fixture
    def debug_build(self, linux):
        b = Build(tree=linux, debug=True, environment={"FOO": "BAR"})
        b.prepare()
        return b

    @pytest.fixture
    def err(self, debug_build, mocker, capfd):
        mocker.patch("time.time", side_effect=[1, 43])
        debug_build.run_cmd(["true"])
        _, e = capfd.readouterr()
        return e

    def test_debug_option(self, debug_build):
        assert debug_build.debug

    def test_log_commands(self, err):
        assert "D: Command: " in err

    def test_log_command_environment(self, err):
        assert "D: Environment: " in err

    def test_log_command_duration(self, err, mocker):
        assert "D: Command finished in 42 seconds" in err


class TestPrepare:
    def test_prepare_runtime_and_wrapper(self, mocker):
        order = []
        mocker.patch(
            "tuxmake.wrapper.Wrapper.prepare_host",
            side_effect=lambda: order.append("wrapper_host"),
        )
        mocker.patch(
            "tuxmake.runtime.NullRuntime.prepare",
            side_effect=lambda: order.append("runtime"),
        )
        mocker.patch(
            "tuxmake.wrapper.Wrapper.prepare_runtime",
            side_effect=lambda _: order.append("wrapper_runtime"),
        )
        build = Build(wrapper="ccache")
        build.prepare()
        assert order == ["wrapper_host", "runtime", "wrapper_runtime"]


class TestMissingArtifacts:
    def test_missing_kernel(self, linux_rw, mocker):
        # hack fakelinux Makefile so that it does not produce a kernel image
        makefile = linux_rw / "Makefile"
        text = makefile.read_text()
        with makefile.open("w") as f:
            for line in text.splitlines():
                if "$(COMPRESS)" not in line:
                    f.write(line)
                    f.write("\n")

        build = Build(tree=linux_rw)
        build.run()
        assert build.failed
        errors, _ = build.parse_log()
        assert errors == 0

    def test_dont_bother_checking_artifacts_if_build_fails(
        self, linux, check_artifacts, monkeypatch
    ):
        monkeypatch.setenv("FAIL", "defconfig")
        build = Build(tree=linux, targets=["config"])
        build.run()
        check_artifacts.assert_not_called()


class TestKernel:
    def test_custom_kernel_image(self, linux):
        build = Build(
            tree=linux,
            target_arch="arm64",
            targets=["kernel"],
            kernel_image="Image.bz2",
        )
        build.run()
        assert build.passed
        assert "Image.bz2" in build.artifacts["kernel"]

    def test_vmlinux(self, linux):
        build = Build(
            tree=linux, target_arch="arm64", targets=["kernel"], kernel_image="vmlinux"
        )
        build.run()
        assert build.passed
        assert "vmlinux" in build.artifacts["kernel"]


class TestKselftest:
    def test_kselftest_merge_before_kselftest(self, linux):
        build = Build(tree=linux, targets=["kselftest", "kselftest-merge"])
        names = [t.name for t in build.targets][-2:]
        assert names == ["kselftest-merge", "kselftest"]

    def test_kselftest_merge_before_kselftest_with_input_already_ordered(self, linux):
        build = Build(tree=linux, targets=["kselftest-merge", "kselftest"])
        names = [t.name for t in build.targets][-2:]
        assert names == ["kselftest-merge", "kselftest"]

    def test_kselftest_without_kselftest_merge(self, linux):
        build = Build(tree=linux, targets=["kselftest"])
        names = [t.name for t in build.targets]
        assert names == ["config", "kselftest"]

    def test_kselftest_merge_runs_right_after_config_and_before_default(self, linux):
        build = Build(tree=linux, targets=["config", "kernel", "kselftest-merge"])
        names = [t.name for t in build.targets]
        assert names == ["config", "kselftest-merge", "default", "kernel"]


class TestHeaders:
    def test_basics(self, linux):
        build = Build(tree=linux, targets=["headers"])
        build.run()
        assert "headers.tar.xz" in build.artifacts["headers"]


class TestCheckEnvironment:
    @pytest.fixture
    def get_command_output(self, mocker):
        return mocker.patch("tuxmake.build.Build.get_command_output")

    def test_basics(self, linux, get_command_output, run_cmd):
        build = Build(tree=linux, target_arch="arm64")
        ccc = "arm-linux-gnu-"
        get_command_output.return_value = ccc
        build.check_environment()
        cmdline = args(run_cmd)
        assert cmdline[0].endswith("/tuxmake-check-environment")
        assert cmdline[1] == "arm64_gcc"
        assert cmdline[2] == "aarch64-linux-gnu-"
        assert cmdline[3] == ccc

    def test_CROSS_COMPILE_COMPAT_not_found(self, linux, run_cmd, get_command_output):
        build = Build(tree=linux, target_arch="arm64")
        get_command_output.return_value = ""
        build.check_environment()
        assert args(run_cmd)[3] == ""

    def test_fails(self, linux, Popen):
        Popen.return_value.returncode = 1
        build = Build(tree=linux)
        with pytest.raises(tuxmake.exceptions.EnvironmentCheckFailed):
            build.check_environment()


class TestReproducible:
    def test_reproducible(self, linux):
        build = Build(tree=linux)
        assert "KBUILD_BUILD_TIMESTAMP" in build.environment
        assert build.environment["KBUILD_BUILD_TIMESTAMP"].startswith("@")
        assert "KBUILD_BUILD_USER" in build.environment
        assert "KBUILD_BUILD_HOST" in build.environment

    def test_reproducible_sets_constant_values(self, linux):
        build1 = Build(tree=linux)
        build2 = Build(tree=linux)
        ts = "KBUILD_BUILD_TIMESTAMP"
        assert build1.environment[ts] == build2.environment[ts]


class TestTerminated:
    def test_signal_handler_raises_exception(self):
        with pytest.raises(Terminated):
            Terminated.handle_signal(15, None)


def q(img):
    return f"{DEFAULT_CONTAINER_REGISTRY}/{img}"


class TestGetImage:
    @pytest.fixture
    def build(self, linux):
        return Build(linux)

    @pytest.fixture
    def toolchain_get_image(self, mocker):
        return mocker.patch("tuxmake.toolchain.Toolchain.get_image")

    def test_image(self, build, toolchain_get_image):
        toolchain_get_image.return_value = "foobarbaz"
        assert get_image(build) == q("foobarbaz")

    def test_override_image(self, build, monkeypatch):
        monkeypatch.setenv("TUXMAKE_IMAGE", "foobar")
        assert get_image(build) == q("foobar")

    def test_override_image_registry(self, build, monkeypatch, toolchain_get_image):
        monkeypatch.setenv("TUXMAKE_IMAGE_REGISTRY", "foobar.com")
        toolchain_get_image.return_value = "myimage"
        assert get_image(build) == "foobar.com/myimage"

    def test_override_image_tag(self, build, monkeypatch, toolchain_get_image):
        monkeypatch.setenv("TUXMAKE_IMAGE_TAG", "20201201")
        toolchain_get_image.return_value = "myimage"
        assert get_image(build) == q("myimage:20201201")

    def test_override_image_registry_and_tag(
        self, build, monkeypatch, toolchain_get_image
    ):
        monkeypatch.setenv("TUXMAKE_IMAGE_REGISTRY", "foobar.com")
        monkeypatch.setenv("TUXMAKE_IMAGE_TAG", "20201201")
        toolchain_get_image.return_value = "myimage"
        assert get_image(build) == "foobar.com/myimage:20201201"

    def test_override_full_image_name_with_registry(self, build, monkeypatch):
        monkeypatch.setenv("TUXMAKE_IMAGE", "docker.io/foo/bar")
        assert get_image(build) == "docker.io/foo/bar"

    def test_detect_dockerhub_registry_on_image_names_with_only_one_component(
        self, build, monkeypatch
    ):
        monkeypatch.setenv("TUXMAKE_IMAGE", "docker.io/foo")
        assert get_image(build) == "docker.io/foo"

    def test_detect_localhost_registry_on_image_names_with_only_one_component(
        self, build, monkeypatch
    ):
        monkeypatch.setenv("TUXMAKE_IMAGE", "localhost/foo")
        assert get_image(build) == "localhost/foo"


class TestCompression:
    def test_default_compression(self, linux):
        build = Build(tree=linux)
        assert build.compression is default_compression
        build.run()
        artifacts = [str(f.name) for f in build.output_dir.glob("*")]
        assert "modules.tar.xz" in artifacts

    def test_compression_none(self, linux):
        build = Build(tree=linux, compression_type="none")
        build.run()
        artifacts = [str(f.name) for f in build.output_dir.glob("*")]
        assert "modules.tar" in artifacts


class TestCustomCrossCompile:
    def test_CROSS_COMPILE(self, linux, Popen):
        build = Build(
            tree=linux, target_arch="arm64", make_variables={"CROSS_COMPILE": "foo-"}
        )
        build.status["config"] = BuildInfo("PASS")
        build.build(build.targets[1])
        assert "CROSS_COMPILE=foo-" in args(Popen)

    def test_CROSS_COMPILE_COMPAT(self, linux, Popen):
        build = Build(
            tree=linux,
            target_arch="arm64",
            make_variables={"CROSS_COMPILE_COMPAT": "foo-"},
        )
        build.get_dynamic_makevars()
        build.status["config"] = BuildInfo("PASS")
        build.build(build.targets[1])
        assert "CROSS_COMPILE_COMPAT=foo-" in args(Popen)


class TestBinDebPkg:
    def test_bindeb_pkg(self, linux):
        build = Build(tree=linux, targets=["bindeb-pkg"])
        build.run()
        assert list(build.output_dir.glob("*.deb")) != []
        assert list(build.output_dir.glob("*.changes")) == []
        assert list(build.output_dir.glob("*.buildinfo")) == []


class TestKorgGCC:
    @pytest.fixture
    def tc_version(self, mocker):
        tc_ver = mocker.patch("tuxmake.runtime.Runtime.get_toolchain_full_version")
        tc_ver.return_value = "14.2.0"
        return tc_ver.return_value

    def test_arm64(self, linux, run_cmd, tc_version):
        b = Build(
            tree=linux,
            targets=["config"],
            toolchain="korg-gcc-13",
            target_arch="arm64",
            runtime="docker",
        )
        b.prepare_korg_gcc_toolchain()
        assert (
            b.korg_gcc_cross_prefix
            == f"{b.build_dir}/gcc-{tc_version}-nolibc/aarch64-linux/bin/aarch64-linux-"
        )

    def test_arm(self, linux, run_cmd, tc_version):
        b = Build(
            tree=linux,
            targets=["config"],
            toolchain="korg-gcc-12",
            target_arch="arm",
            runtime="docker",
        )
        b.prepare_korg_gcc_toolchain()
        assert (
            b.korg_gcc_cross_prefix
            == f"{b.build_dir}/gcc-{tc_version}-nolibc/arm-linux-gnueabi/bin/arm-linux-gnueabi-"
        )

    def test_openrisc(self, linux, run_cmd, tc_version):
        b = Build(
            tree=linux,
            targets=["config"],
            toolchain="korg-gcc-11",
            target_arch="openrisc",
            runtime="docker",
        )
        b.prepare_korg_gcc_toolchain()
        assert (
            b.korg_gcc_cross_prefix
            == f"{b.build_dir}/gcc-{tc_version}-nolibc/or1k-linux/bin/or1k-linux-"
        )

    def test_parisc(self, linux, run_cmd, tc_version):
        b = Build(
            tree=linux,
            targets=["config"],
            toolchain="korg-gcc-10",
            target_arch="parisc",
            runtime="docker",
        )
        b.prepare_korg_gcc_toolchain()
        assert (
            b.korg_gcc_cross_prefix
            == f"{b.build_dir}/gcc-{tc_version}-nolibc/hppa-linux/bin/hppa-linux-"
        )

    def test_x86_64(self, linux, run_cmd, tc_version):
        b = Build(
            tree=linux,
            targets=["config"],
            toolchain="korg-gcc-9",
            target_arch="x86_64",
            runtime="docker",
        )
        b.prepare_korg_gcc_toolchain()
        assert (
            b.korg_gcc_cross_prefix
            == f"{b.build_dir}/gcc-{tc_version}-nolibc/x86_64-linux/bin/x86_64-linux-"
        )

    def test_prepare_korg_gcc_toolchain_called(self, mocker, linux):
        mocker.patch("tuxmake.build.Build.prepare_korg_gcc_toolchain")
        b = Build(tree=linux, toolchain="korg-gcc", target_arch="arm64")
        b.run()
        assert b.prepare_korg_gcc_toolchain.call_count == 1

    def test_prepare_korg_gcc_toolchain_fail(self, linux, run_cmd):
        run_cmd.return_value = False
        b = Build(
            tree=linux,
            targets=["config"],
            toolchain="korg-gcc",
            target_arch="x86_64",
            runtime="docker",
        )
        with pytest.raises(tuxmake.exceptions.KorgGccPreparationFailed):
            b.prepare_korg_gcc_toolchain()

    def test_korg_gcc_cross_prefix(self, linux, Popen, run_cmd, tc_version):
        b = Build(
            tree=linux,
            toolchain="korg-gcc-12",
            target_arch="x86_64",
            runtime="docker",
        )
        b.prepare_korg_gcc_toolchain()
        b.get_dynamic_makevars()
        b.build(b.targets[0])
        args = b.expand_cmd_part(b.targets[0].commands[0][0], b.makevars)
        assert f"CROSS_COMPILE={b.korg_gcc_cross_prefix}" in args

    def test_korg_toolchains_dir(self, linux, run_cmd, tmp_path):
        b = Build(
            tree=linux,
            toolchain="korg-gcc",
            target_arch="x86_64",
            runtime="docker",
            korg_toolchains_dir=tmp_path,
        )
        assert b.korg_toolchains_dir == tmp_path
        # Access korg_toolchains_dir once again and assert
        b.prepare_korg_gcc_toolchain()
        assert b.korg_toolchains_dir == tmp_path


class TestKorgGccDownloadAll:
    @pytest.fixture
    def get_command_output(self, mocker):
        return mocker.patch("tuxmake.build.Build.get_command_output")

    def test_basics(self, linux, get_command_output, run_cmd):
        build = Build()
        build.download_all_korg_gcc_toolchains()
        cmdline = args(run_cmd)
        assert cmdline[0].endswith("/tuxmake-download-all-korg-toolchains")
        assert cmdline[1].endswith("/korg_toolchains")

    def test_with_korg_cache_dir(self, linux, get_command_output, run_cmd, tmp_path):
        build = Build(korg_toolchains_dir=str(tmp_path))
        build.download_all_korg_gcc_toolchains()
        cmdline = args(run_cmd)
        assert cmdline[0].endswith("/tuxmake-download-all-korg-toolchains")
        assert cmdline[1].endswith(f"{tmp_path}")

    def test_fails(self, linux, run_cmd):
        run_cmd.return_value = False
        build = Build()
        with pytest.raises(tuxmake.exceptions.KorgGccDownloadAllToolchainFailed):
            build._download_all_korg_gcc_toolchains("14.2.0")
