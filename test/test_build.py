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
from tuxmake.build import defaults
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


@pytest.fixture()
def Popen(mocker, check_artifacts):
    _Popen = mocker.patch("subprocess.Popen")
    _Popen.return_value.communicate.return_value = (
        mocker.MagicMock(),
        mocker.MagicMock(),
    )
    return _Popen


# Disable the metadata extraction for non-metadata related tests since its
# pretty slow.
@pytest.fixture(autouse=True)
def disable_metadata(mocker):
    return mocker.patch("tuxmake.build.Build.extract_metadata")


def args(called):
    return called.call_args[0][0]


def kwargs(called):
    return called.call_args[1]


def test_invalid_directory(tmp_path):
    (tmp_path / "Makefile").touch()
    with pytest.raises(tuxmake.exceptions.UnrecognizedSourceTree):
        build(tree=tmp_path)


def test_build(linux, home, kernel):
    result = build(tree=linux)
    assert kernel in result.artifacts["kernel"]
    assert (home / ".cache/tuxmake/builds/1" / kernel).exists()
    assert result.passed


def test_build_with_output_dir(linux, output_dir, kernel):
    result = build(tree=linux, output_dir=output_dir)
    assert kernel in result.artifacts["kernel"]
    assert (output_dir / kernel).exists()
    assert result.output_dir == output_dir


def test_build_with_build_dir(linux, tmp_path):
    build(tree=linux, build_dir=tmp_path)
    assert (tmp_path / ".config").exists


def test_no_directory_created_unecessarily(linux, home):
    Build(tree=linux)
    assert len(list(home.glob("*"))) == 0


def test_no_directory_created_unecessarily_with_explicit_paths(linux, tmp_path):
    Build(tree=linux, output_dir=tmp_path / "output", build_dir=tmp_path / "build")
    assert not (tmp_path / "output").exists()
    assert not (tmp_path / "build").exists()


def test_unsupported_target(linux):
    with pytest.raises(tuxmake.exceptions.UnsupportedTarget):
        build(tree=linux, targets=["unknown-target"])


def test_kconfig_default(linux, Popen):
    b = Build(tree=linux, targets=["config"])
    b.build(b.targets[0])
    assert "defconfig" in args(Popen)


def test_kconfig_named(linux, Popen):
    b = Build(tree=linux, targets=["config"], kconfig="fooconfig")
    b.build(b.targets[0])
    assert "fooconfig" in args(Popen)


def test_kconfig_named_invalid(linux, mocker):
    with pytest.raises(tuxmake.exceptions.UnsupportedKconfig):
        build(tree=linux, targets=["config"], kconfig="foobar")


def test_kconfig_url(linux, mocker, output_dir):
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


def test_kconfig_url_not_found(linux, mocker):
    mocker.patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.HTTPError(
            "https://example.com/config.txt", 404, "Not Found", {}, None
        ),
    )

    with pytest.raises(tuxmake.exceptions.InvalidKConfig):
        build(tree=linux, targets=["config"], kconfig="https://example.com/config.txt")


def test_kconfig_localfile(linux, tmp_path, output_dir):
    extra_config = tmp_path / "extra_config"
    extra_config.write_text("CONFIG_XYZ=y\nCONFIG_ABC=m\n")
    build(
        tree=linux, targets=["config"], kconfig=str(extra_config), output_dir=output_dir
    )
    config = output_dir / "config"
    assert "CONFIG_XYZ=y\nCONFIG_ABC=m\n" in config.read_text()


def test_kconfig_add_url(linux, mocker, output_dir):
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


def test_kconfig_add_localfile(linux, tmp_path, output_dir):
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


def test_kconfig_add_inline(linux, output_dir):
    build(
        tree=linux,
        targets=["config"],
        kconfig_add=["CONFIG_FOO=y"],
        output_dir=output_dir,
    )
    config = output_dir / "config"
    assert "CONFIG_FOO=y\n" in config.read_text()


def test_kconfig_add_inline_not_set(linux, output_dir):
    build(
        tree=linux,
        targets=["config"],
        kconfig_add=["# CONFIG_FOO is not set"],
        output_dir=output_dir,
    )
    config = output_dir / "config"
    assert "CONFIG_FOO is not set\n" in config.read_text()


def test_kconfig_add_inline_set_to_no(linux, output_dir):
    build(
        tree=linux,
        targets=["config"],
        kconfig_add=["CONFIG_FOO=n"],
        output_dir=output_dir,
    )
    config = output_dir / "config"
    assert "CONFIG_FOO=n\n" in config.read_text()


def test_kconfig_add_in_tree(linux, output_dir):
    build(
        tree=linux,
        targets=["config"],
        kconfig_add=["kvm_guest.config", "qemu-gdb.config"],
        output_dir=output_dir,
    )
    config = output_dir / "config"
    assert ("CONFIG_KVM_GUEST=y") in config.read_text()
    assert ("CONFIG_DEBUG_INFO=y") in config.read_text()


def test_kconfig_add_invalid(linux):
    with pytest.raises(tuxmake.exceptions.UnsupportedKconfigFragment):
        build(tree=linux, targets=["config"], kconfig_add=["foo"])


def test_output_dir(linux, output_dir, kernel):
    build(tree=linux, output_dir=output_dir)
    artifacts = [str(f.name) for f in output_dir.glob("*")]
    assert "config" in artifacts
    assert kernel in artifacts
    assert "arch" not in artifacts


def test_saves_log(linux):
    result = build(tree=linux)
    artifacts = [str(f.name) for f in result.output_dir.glob("*")]
    assert "build.log" in result.artifacts["log"]
    assert "build.log" in artifacts
    log = result.output_dir / "build.log"
    assert "make --silent" in log.read_text()


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
    assert err == ""


def test_ctrl_c(linux, mocker, Popen):
    mocker.patch("tuxmake.build.Build.logger")
    process = mocker.MagicMock()
    Popen.return_value = process
    process.communicate.side_effect = KeyboardInterrupt()
    with pytest.raises(SystemExit):
        b = Build(tree=linux)
        b.build(b.targets[0])
    process.terminate.assert_called()


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

    def test_invalid_arch(self):
        with pytest.raises(tuxmake.exceptions.UnsupportedArchitecture):
            Architecture("foobar")


class TestToolchain:
    # Test that the righ make arguments are passed, when needed. Ideally we
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

    def test_clang(self, linux, Popen):
        b = Build(tree=linux, targets=["config"], toolchain="clang")
        b.build(b.targets[0])
        cmdline = args(Popen)
        assert "CC=clang" in cmdline

    def test_invalid_toolchain(self):
        with pytest.raises(tuxmake.exceptions.UnsupportedToolchain):
            Toolchain("foocc")


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
    def oldlinux(self, linux, tmp_path):
        old = tmp_path / "oldlinux"
        shutil.copytree(linux, old)
        subprocess.check_call(
            ["sed", "-i", "-e", "s/dtbs_install/XXXX/g", str(old / "Makefile")]
        )
        return old

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
        monkeypatch.setattr(dtbs_legacy, "commands", [["false"]])
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
        result = build(tree=linux, targets=["modules"])
        assert result.status["config"].passed
        assert result.status["modules"].passed


class TestRuntime:
    def test_null(self, linux):
        build = Build(tree=linux)
        assert build.runtime

    def test_docker(self, linux):
        build = Build(tree=linux, runtime="docker")
        assert build.runtime

    def test_interactive_command(self, linux, mocker):
        runtime = mocker.patch("tuxmake.build.get_runtime").return_value
        runtime.get_command_line.return_value = ["true"]
        build = Build(tree=linux, runtime="docker")
        build.run_cmd(["true"], interactive=True)
        runtime.get_command_line.assert_called_with(build, ["true"], True)


class TestEnvironment:
    def test_basics(self, linux, Popen):
        b = Build(
            tree=linux,
            environment={"KCONFIG_ALLCONFIG": "foo.config"},
            targets=["config"],
        )
        b.build(b.targets[0])
        assert kwargs(Popen)["env"]["KCONFIG_ALLCONFIG"] == "foo.config"


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
        b.build(b.targets[0])
        assert "CC=ccache gcc" in args(Popen)
        assert "HOSTCC=ccache gcc" in args(Popen)
        assert "CCACHE_DIR" in kwargs(Popen)["env"]

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


LOG = (Path(__file__).parent / "logs/simple.log").read_text()


class TestParseLog:
    @pytest.fixture(scope="class")
    def build(self, linux):
        b = Build(tree=linux)
        (b.output_dir / "build.log").write_text(LOG)
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
    @pytest.fixture
    def debug_build(self, linux):
        return Build(tree=linux, debug=True, environment={"FOO": "BAR"})

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
    def test_prepare_runtime_first(self, mocker):
        order = []
        mocker.patch(
            "tuxmake.runtime.NullRuntime.prepare",
            side_effect=lambda _: order.append("runtime"),
        )
        mocker.patch(
            "tuxmake.wrapper.Wrapper.prepare",
            side_effect=lambda _: order.append("wrapper"),
        )
        build = Build(wrapper="ccache")
        build.prepare()
        assert order[0] == "runtime"


class TestMissingArtifacts:
    def test_missing_kernel(self, linux, mocker):
        # hack fakelinux Makefile so that it does not produce a kernel image
        makefile = Path(linux) / "Makefile"
        text = makefile.read_text()
        with makefile.open("w") as f:
            for line in text.splitlines():
                if "$(COMPRESS)" not in line:
                    f.write(line)
                    f.write("\n")

        build = Build(tree=linux)
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
