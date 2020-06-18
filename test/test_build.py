import pytest
from tuxmake.arch import Architecture
from tuxmake.toolchain import Toolchain
from tuxmake.build import build
from tuxmake.build import Build
from tuxmake.build import defaults
import tuxmake.exceptions


@pytest.fixture
def arch():
    return Architecture(defaults.target_arch)


@pytest.fixture
def output_dir(tmp_path):
    out = tmp_path / "output"
    return out


def test_build(linux, home, arch):
    result = build(linux)
    assert arch.kernel in result.artifacts
    assert (home / ".cache/tuxmake/builds/1" / arch.kernel).exists()


def test_build_with_output_dir(linux, output_dir, arch):
    result = build(linux, output_dir=output_dir)
    assert arch.kernel in result.artifacts
    assert (output_dir / arch.kernel).exists()
    assert result.output_dir == output_dir


def test_unsupported_target(linux):
    with pytest.raises(tuxmake.exceptions.UnsupportedTarget):
        build(linux, targets=["unknown-target"])


def test_kconfig_default(linux, mocker):
    check_call = mocker.patch("subprocess.check_call")
    mocker.patch("tuxmake.build.Build.copy_artifacts")
    mocker.patch("tuxmake.build.Build.cleanup")
    build(linux, targets=["config"])
    assert "defconfig" in check_call.call_args_list[0][0][0]


def test_kconfig_named(linux, mocker):
    check_call = mocker.patch("subprocess.check_call")
    mocker.patch("tuxmake.build.Build.copy_artifacts")
    mocker.patch("tuxmake.build.Build.cleanup")
    build(linux, targets=["config"], kconfig=["fooconfig"])
    assert "fooconfig" in check_call.call_args_list[0][0][0]


def test_kconfig_url(linux, mocker, output_dir):
    response = mocker.MagicMock()
    response.getcode.return_value = 200
    response.read.return_value = b"CONFIG_FOO=y\nCONFIG_BAR=y\n"
    mocker.patch("tuxmake.build.urlopen", return_value=response)

    build(
        linux,
        targets=["config"],
        kconfig=["defconfig", "https://example.com/config.txt"],
        output_dir=output_dir,
    )
    config = output_dir / "config"
    assert "CONFIG_FOO=y\nCONFIG_BAR=y\n" in config.read_text()


def test_kconfig_localfile(linux, tmp_path, output_dir):
    extra_config = tmp_path / "extra_config"
    extra_config.write_text("CONFIG_XYZ=y\nCONFIG_ABC=m\n")
    build(
        linux,
        targets=["config"],
        kconfig=["defconfig", str(extra_config)],
        output_dir=output_dir,
    )
    config = output_dir / "config"
    assert "CONFIG_XYZ=y\nCONFIG_ABC=m\n" in config.read_text()


def test_output_dir(linux, output_dir, arch):
    build(linux, output_dir=output_dir)
    artifacts = [str(f.name) for f in output_dir.glob("*")]
    assert "config" in artifacts
    assert arch.kernel in artifacts
    assert "arch" not in artifacts


def test_saves_log(linux):
    result = build(linux)
    artifacts = [str(f.name) for f in result.output_dir.glob("*")]
    assert "build.log" in result.artifacts
    assert "build.log" in artifacts
    log = result.output_dir / "build.log"
    assert "make --silent" in log.read_text()


def test_build_failure(linux, monkeypatch):
    monkeypatch.setenv("FAIL", "kernel")
    result = build(linux, targets=["config", "kernel"])
    assert not result.passed
    assert result.failed
    artifacts = [str(f.name) for f in result.output_dir.glob("*")]
    assert "build.log" in artifacts
    assert "config" in artifacts
    assert result.arch.kernel not in artifacts


class TestArchitecture:
    def test_x86_64(self, linux):
        result = build(linux, target_arch="x86_64")
        assert "bzImage" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_arm64(self, linux):
        result = build(linux, target_arch="arm64")
        assert "Image.gz" in [str(f.name) for f in result.output_dir.glob("*")]

    def test_invalid_arch(self):
        with pytest.raises(tuxmake.exceptions.UnsupportedArchitecture):
            Architecture("foobar")


@pytest.fixture
def builder(linux, output_dir, mocker):
    mocker.patch("tuxmake.build.Build.cleanup")
    mocker.patch("tuxmake.build.Build.copy_artifacts")
    b = Build(linux, output_dir / "tmp", output_dir)
    return b


class TestToolchain:
    # Test that the righ CC= argument is passed. Ideally we want more black box
    # tests that check the results of the build, but for that we need a
    # mechanism to check which toolchain was used to build a given binary (and
    # for test/fakelinux/ to produce real binaries)
    def test_gcc_10(self, builder, mocker):
        check_call = mocker.patch("subprocess.check_call")
        builder.toolchain = Toolchain("gcc-10")
        builder.build("config")
        cmdline = check_call.call_args[0][0]
        cross = builder.arch.makevars["CROSS_COMPILE"]
        assert f"CC={cross}gcc-10" in cmdline

    def test_clang(self, builder, mocker):
        check_call = mocker.patch("subprocess.check_call")
        builder.toolchain = Toolchain("clang")
        builder.build("config")
        cmdline = check_call.call_args[0][0]
        assert "CC=clang" in cmdline

    def test_invalid_toolchain(self, builder):
        with pytest.raises(tuxmake.exceptions.UnsupportedToolchain):
            Toolchain("foocc")
