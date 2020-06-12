import pytest
import tuxmake


@pytest.fixture
def output_dir(tmp_path):
    out = tmp_path / "output"
    return out


def test_build(linux, home):
    build = tuxmake.build(linux)
    assert "arch/x86/boot/bzImage" in build.artifacts
    assert (home / ".cache/tuxmake/builds/1/arch/x86/boot/bzImage").exists()


def test_build_with_output_dir(linux, output_dir):
    build = tuxmake.build(linux, output_dir=output_dir)
    assert "arch/x86/boot/bzImage" in build.artifacts
    assert (output_dir / "arch/x86/boot/bzImage").exists()
    assert build.output_dir == output_dir
