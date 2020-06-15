import pytest
from tuxmake.build import build
import tuxmake.exceptions


@pytest.fixture
def output_dir(tmp_path):
    out = tmp_path / "output"
    return out


def test_build(linux, home):
    result = build(linux)
    assert "arch/x86/boot/bzImage" in result.artifacts
    assert (home / ".cache/tuxmake/builds/1/arch/x86/boot/bzImage").exists()


def test_build_with_output_dir(linux, output_dir):
    result = build(linux, output_dir=output_dir)
    assert "arch/x86/boot/bzImage" in result.artifacts
    assert (output_dir / "arch/x86/boot/bzImage").exists()
    assert result.output_dir == output_dir


def test_unsupported_target(linux):
    with pytest.raises(tuxmake.exceptions.InvalidTarget):
        build(linux, targets=["unknown-target"])


def test_kconfig_default(linux, mocker):
    check_call = mocker.patch("subprocess.check_call")
    build(linux, targets=["config"])
    assert "defconfig" in check_call.call_args_list[0].args[0]


def test_kconfig_named(linux, mocker):
    check_call = mocker.patch("subprocess.check_call")
    build(linux, targets=["config"], kconfig=["fooconfig"])
    assert "fooconfig" in check_call.call_args_list[0].args[0]


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
    config = output_dir / ".config"
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
    config = output_dir / ".config"
    assert "CONFIG_XYZ=y\nCONFIG_ABC=m\n" in config.read_text()
