import pytest
import urllib
from tuxmake.arch import Architecture, Native
from tuxmake.target import Target
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


def test_invalid_directory(tmp_path):
    (tmp_path / "Makefile").touch()
    with pytest.raises(tuxmake.exceptions.UnrecognizedSourceTree):
        build(tmp_path)


def test_build(linux, home, kernel):
    result = build(linux)
    assert kernel in result.artifacts
    assert (home / ".cache/tuxmake/builds/1" / kernel).exists()


def test_build_with_output_dir(linux, output_dir, kernel):
    result = build(linux, output_dir=output_dir)
    assert kernel in result.artifacts
    assert (output_dir / kernel).exists()
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
    build(linux, targets=["config"], kconfig="fooconfig")
    assert "fooconfig" in check_call.call_args_list[0][0][0]


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


def test_concurrency_default(linux, mocker):
    check_call = mocker.patch("subprocess.check_call")
    mocker.patch("tuxmake.build.Build.copy_artifacts")
    mocker.patch("tuxmake.build.Build.cleanup")
    build(linux, targets=["config"])
    assert f"--jobs={defaults.jobs}" in check_call.call_args[0][0]


def test_concurrency_set(linux, mocker):
    check_call = mocker.patch("subprocess.check_call")
    mocker.patch("tuxmake.build.Build.copy_artifacts")
    mocker.patch("tuxmake.build.Build.cleanup")
    build(linux, targets=["config"], jobs=99)
    assert "--jobs=99" in check_call.call_args[0][0]


def test_verbose(linux, mocker):
    check_call = mocker.patch("subprocess.check_call")
    mocker.patch("tuxmake.build.Build.copy_artifacts")
    mocker.patch("tuxmake.build.Build.cleanup")
    build(linux, targets=["config"], verbose=True)
    assert "--silent" not in check_call.call_args[0][0]


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
    b = Build(linux, output_dir=output_dir)
    return b


class TestToolchain:
    # Test that the righ CC= argument is passed. Ideally we want more black box
    # tests that check the results of the build, but for that we need a
    # mechanism to check which toolchain was used to build a given binary (and
    # for test/fakelinux/ to produce real binaries)
    def test_gcc_10(self, builder, mocker):
        check_call = mocker.patch("subprocess.check_call")
        builder.toolchain = Toolchain("gcc-10")
        builder.build(Target("config", builder))
        cmdline = check_call.call_args[0][0]
        assert "CC=gcc-10" in cmdline

    def test_gcc_10_cross(self, builder, mocker):
        check_call = mocker.patch("subprocess.check_call")
        builder.toolchain = Toolchain("gcc-10")
        builder.target_arch = Architecture("arm64")
        builder.build(Target("config", builder))
        cmdline = check_call.call_args[0][0]
        assert "CC=aarch64-linux-gnu-gcc-10" in cmdline

    def test_clang(self, builder, mocker):
        check_call = mocker.patch("subprocess.check_call")
        builder.toolchain = Toolchain("clang")
        builder.build(Target("config", builder))
        cmdline = check_call.call_args[0][0]
        assert "CC=clang" in cmdline

    def test_invalid_toolchain(self, builder):
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
