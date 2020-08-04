import json
import pytest
import re
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


@pytest.fixture()
def Popen(mocker):
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
        build(tmp_path)


def test_build(linux, home, kernel):
    result = build(linux)
    assert kernel in result.artifacts
    assert (home / ".cache/tuxmake/builds/1" / kernel).exists()
    assert result.passed


def test_build_with_output_dir(linux, output_dir, kernel):
    result = build(linux, output_dir=output_dir)
    assert kernel in result.artifacts
    assert (output_dir / kernel).exists()
    assert result.output_dir == output_dir


def test_unsupported_target(linux):
    with pytest.raises(tuxmake.exceptions.UnsupportedTarget):
        build(linux, targets=["unknown-target"])


def test_kconfig_default(linux, Popen):
    b = Build(linux, targets=["config"])
    b.build(b.targets[0])
    assert "defconfig" in args(Popen)


def test_kconfig_named(linux, Popen):
    b = Build(linux, targets=["config"], kconfig="fooconfig")
    b.build(b.targets[0])
    assert "fooconfig" in args(Popen)


def test_kconfig_named_invalid(linux, mocker):
    with pytest.raises(tuxmake.exceptions.UnsupportedKconfig):
        build(linux, targets=["config"], kconfig="foobar")


def test_kconfig_url(linux, mocker, output_dir):
    response = mocker.MagicMock()
    response.getcode.return_value = 200
    response.read.return_value = b"CONFIG_FOO=y\nCONFIG_BAR=y\n"
    mocker.patch("urllib.request.urlopen", return_value=response)

    build(
        linux,
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
        build(linux, targets=["config"], kconfig="https://example.com/config.txt")


def test_kconfig_localfile(linux, tmp_path, output_dir):
    extra_config = tmp_path / "extra_config"
    extra_config.write_text("CONFIG_XYZ=y\nCONFIG_ABC=m\n")
    build(linux, targets=["config"], kconfig=str(extra_config), output_dir=output_dir)
    config = output_dir / "config"
    assert "CONFIG_XYZ=y\nCONFIG_ABC=m\n" in config.read_text()


def test_kconfig_add_url(linux, mocker, output_dir):
    response = mocker.MagicMock()
    response.getcode.return_value = 200
    response.read.return_value = b"CONFIG_FOO=y\nCONFIG_BAR=y\n"
    mocker.patch("urllib.request.urlopen", return_value=response)

    build(
        linux,
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
        linux,
        targets=["config"],
        kconfig_add=[str(extra_config)],
        output_dir=output_dir,
    )
    config = output_dir / "config"
    assert "CONFIG_XYZ=y\nCONFIG_ABC=m\n" in config.read_text()


def test_kconfig_add_inline(linux, output_dir):
    build(
        linux, targets=["config"], kconfig_add=["CONFIG_FOO=y"], output_dir=output_dir
    )
    config = output_dir / "config"
    assert "CONFIG_FOO=y\n" in config.read_text()


def test_kconfig_add_inline_not_set(linux, output_dir):
    build(
        linux,
        targets=["config"],
        kconfig_add=["# CONFIG_FOO is not set"],
        output_dir=output_dir,
    )
    config = output_dir / "config"
    assert "CONFIG_FOO is not set\n" in config.read_text()


def test_kconfig_add_in_tree(linux, output_dir):
    build(
        linux,
        targets=["config"],
        kconfig_add=["kvm_guest.config"],
        output_dir=output_dir,
    )
    config = output_dir / "config"
    assert "CONFIG_KVM_GUEST=y" in config.read_text()


def test_kconfig_add_invalid(linux):
    with pytest.raises(tuxmake.exceptions.UnsupportedKconfigFragment):
        build(linux, targets=["config"], kconfig_add=["foo"])


def test_output_dir(linux, output_dir, kernel):
    build(linux, output_dir=output_dir)
    artifacts = [str(f.name) for f in output_dir.glob("*")]
    assert "config" in artifacts
    assert kernel in artifacts
    assert "arch" not in artifacts


def test_saves_log(linux):
    result = build(linux)
    artifacts = [str(f.name) for f in result.output_dir.glob("*")]
    assert "build.log" in result.artifacts
    assert "build.log" in artifacts
    log = result.output_dir / "build.log"
    assert "make --silent" in log.read_text()


def test_build_failure(linux, kernel, monkeypatch):
    monkeypatch.setenv("FAIL", "kernel")
    result = build(linux, targets=["config", "kernel"])
    assert not result.passed
    assert result.failed
    artifacts = [str(f.name) for f in result.output_dir.glob("*")]
    assert "build.log" in artifacts
    assert "config" in artifacts
    assert kernel not in artifacts


def test_concurrency_default(linux, Popen):
    b = Build(linux, targets=["config"])
    b.build(b.targets[0])
    assert f"--jobs={defaults.jobs}" in args(Popen)


def test_concurrency_set(linux, Popen):
    b = Build(linux, targets=["config"], jobs=99)
    b.build(b.targets[0])
    assert "--jobs=99" in args(Popen)


def test_verbose(linux, mocker, Popen):
    b = Build(linux, targets=["config"], verbose=True)
    b.build(b.targets[0])
    assert "--silent" not in args(Popen)


def test_quiet(linux, capfd):
    build(linux, quiet=True)
    out, err = capfd.readouterr()
    assert out == ""
    assert err == ""


def test_ctrl_c(linux, mocker, Popen):
    mocker.patch("tuxmake.build.Build.logger")
    process = mocker.MagicMock()
    Popen.return_value = process
    process.communicate.side_effect = KeyboardInterrupt()
    with pytest.raises(SystemExit):
        b = Build(linux)
        b.build(b.targets[0])
    process.terminate.assert_called()


class TestArchitecture:
    def test_x86_64(self, linux):
        result = build(linux, target_arch="x86_64")
        assert "bzImage" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_arm64(self, linux):
        result = build(linux, target_arch="arm64")
        assert "Image.gz" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_arm(self, linux):
        result = build(linux, target_arch="arm")
        assert "zImage" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_i386(self, linux):
        result = build(linux, target_arch="i386")
        assert "bzImage" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_mips(self, linux):
        result = build(linux, target_arch="mips")
        assert "vmlinux.bin.gz" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_riscv(self, linux):
        result = build(linux, target_arch="riscv")
        assert "Image.gz" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_arc(self, linux):
        result = build(linux, target_arch="arc")
        assert "uImage.gz" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_invalid_arch(self):
        with pytest.raises(tuxmake.exceptions.UnsupportedArchitecture):
            Architecture("foobar")


class TestToolchain:
    # Test that the righ CC= argument is passed. Ideally we want more black box
    # tests that check the results of the build, but for that we need a
    # mechanism to check which toolchain was used to build a given binary (and
    # for test/fakelinux/ to produce real binaries)
    def test_gcc_10(self, linux, Popen):
        b = Build(linux, targets=["config"], toolchain="gcc-10")
        b.build(b.targets[0])
        cmdline = args(Popen)
        assert "CC=gcc-10" in cmdline

    def test_gcc_10_cross(self, linux, Popen):
        b = Build(linux, targets=["config"], toolchain="gcc-10", target_arch="arm64")
        b.build(b.targets[0])
        cmdline = args(Popen)
        assert "CC=aarch64-linux-gnu-gcc-10" in cmdline

    def test_clang(self, linux, Popen):
        b = Build(linux, targets=["config"], toolchain="clang")
        b.build(b.targets[0])
        cmdline = args(Popen)
        assert "CC=clang" in cmdline

    def test_invalid_toolchain(self):
        with pytest.raises(tuxmake.exceptions.UnsupportedToolchain):
            Toolchain("foocc")


class TestDebugKernel:
    def test_build_with_debugkernel(self, linux):
        result = build(linux, targets=["config", "debugkernel"])
        artifacts = [str(f.name) for f in result.output_dir.glob("*")]
        assert "vmlinux" in artifacts

    def test_build_with_debugkernel_arm64(self, linux):
        result = build(linux, targets=["config", "debugkernel"], target_arch="arm64")
        artifacts = [str(f.name) for f in result.output_dir.glob("*")]
        assert "vmlinux" in artifacts


class TestModules:
    def test_modules(self, linux):
        result = build(linux, targets=["config", "kernel", "modules"])
        artifacts = [str(f.name) for f in result.output_dir.glob("*")]
        assert "modules.tar.gz" in artifacts

    def test_skip_if_not_configured_for_modules(self, linux):
        result = build(
            linux, targets=["config", "kernel", "modules"], kconfig="tinyconfig"
        )
        artifacts = [str(f.name) for f in result.output_dir.glob("*")]
        assert "modules.tar.gz" not in artifacts


class TestDtbs:
    def test_dtbs(self, linux):
        result = build(linux, targets=["dtbs"], target_arch="arm64")
        artifacts = [str(f.name) for f in result.output_dir.glob("*")]
        assert "dtbs.tar.gz" in artifacts

    def test_skip_on_arch_with_no_dtbs(self, linux):
        result = build(linux, targets=["dtbs"], target_arch="x86_64")
        artifacts = [str(f.name) for f in result.output_dir.glob("*")]
        assert "dtbs.tar.gz" not in artifacts


class TestTargetDependencies:
    def test_dont_build_kernel_if_config_fails(self, linux, monkeypatch):
        monkeypatch.setenv("FAIL", "defconfig")
        result = build(linux)
        assert result.status["config"].failed
        assert result.status["kernel"].skipped

    def test_include_dependencies_in_targets(self, linux):
        result = build(linux, targets=["kernel"])
        assert result.status["config"].passed
        assert result.status["kernel"].passed

    def test_recursive_dependencies(self, linux):
        result = build(linux, targets=["modules"])
        assert result.status["config"].passed
        assert result.status["kernel"].passed
        assert result.status["modules"].passed


class TestRuntime:
    def test_null(self, linux):
        build = Build(linux)
        assert build.runtime

    def test_docker(self, linux):
        build = Build(linux, runtime="docker")
        assert build.runtime


class TestEnvironment:
    def test_basics(self, linux, Popen):
        b = Build(
            linux, environment={"KCONFIG_ALLCONFIG": "foo.config"}, targets=["config"]
        )
        b.build(b.targets[0])
        assert kwargs(Popen)["env"]["KCONFIG_ALLCONFIG"] == "foo.config"


class TestCompilerWrappers:
    def test_ccache(self, linux, Popen):
        b = Build(linux, targets=["config"], wrapper="ccache")
        b.build(b.targets[0])
        assert "CC=ccache gcc" in args(Popen)
        assert "HOSTCC=ccache gcc" in args(Popen)
        assert "CCACHE_DIR" in kwargs(Popen)["env"]

    def test_ccache_gcc_v(self, linux, Popen):
        b = Build(linux, targets=["config"], toolchain="gcc-10", wrapper="ccache")
        b.build(b.targets[0])
        assert "CC=ccache gcc-10" in args(Popen)
        assert "HOSTCC=ccache gcc-10" in args(Popen)

    def test_ccache_target_arch(self, linux, Popen):
        b = Build(linux, targets=["config"], target_arch="arm64", wrapper="ccache")
        b.build(b.targets[0])
        assert "CC=ccache aarch64-linux-gnu-gcc" in args(Popen)

    def test_ccache_target_arch_and_gcc_v(self, linux, Popen):
        b = Build(
            linux,
            targets=["config"],
            toolchain="gcc-10",
            target_arch="arm64",
            wrapper="ccache",
        )
        b.build(b.targets[0])
        assert "CC=ccache aarch64-linux-gnu-gcc-10" in args(Popen)


@pytest.mark.skipif(
    [int(n) for n in pytest.__version__.split(".")] < [3, 10], reason="old pytest"
)
class TestMetadata:
    @pytest.fixture(scope="class")
    def build(self, linux):
        build = Build(linux, environment={"WARN": "kernel", "FAIL": "modules"})
        build.run()
        return build

    def test_kernelversion(self, build):
        assert re.match(r"^[0-9]+\.[0-9]+", build.metadata["source"]["kernelversion"])

    def test_metadata_file(self, build):
        metadata_file = build.output_dir / "metadata.json"
        assert metadata_file.exists()
        assert type(json.loads(metadata_file.open().read())) is dict

    def test_build_metadata(self, build):
        assert type(build.metadata["build"]) is dict

    def test_status(self, build):
        assert build.metadata["results"]["status"] == "FAIL"


LOG = """error: asdasdas
warning: ssadas
"""


class TestParseLog:
    @pytest.fixture(scope="class")
    def build(linux):
        b = Build(linux)
        (b.output_dir / "build.log").write_text(LOG)
        return b

    def test_warnings(self, build):
        _, warnings = build.parse_log()
        assert warnings == 1

    def test_errors(self, build):
        errors, _ = build.parse_log()
        assert errors == 1
