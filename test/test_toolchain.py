import pytest

from tuxmake.arch import Architecture
from tuxmake.arch import Native
from tuxmake.toolchain import Toolchain
from tuxmake.toolchain import NoExplicitToolchain


@pytest.fixture
def gcc():
    return Toolchain("gcc")


@pytest.fixture
def arm64():
    return Architecture("arm64")


@pytest.fixture
def korg_gcc():
    return Toolchain("korg-gcc")


class TestGcc:
    def test_image(self, gcc, arm64):
        assert gcc.get_image(arm64) == "tuxmake/arm64_gcc"


class TestKorgGcc:
    def test_image(self, korg_gcc, arm64):
        assert korg_gcc.get_image(arm64) == "tuxmake/korg-gcc"

    def test_suffix(self, korg_gcc):
        assert korg_gcc.suffix() == "linux"


@pytest.fixture
def clang():
    return Toolchain("clang")


class TestClang:
    def test_image(self, clang, arm64):
        assert clang.get_image(arm64) == "tuxmake/arm64_clang"


def test_compiler_name(gcc, arm64):
    default = NoExplicitToolchain()
    assert gcc.compiler(Native()) == "gcc"
    assert gcc.compiler(arm64) == "aarch64-linux-gnu-gcc"
    assert default.compiler(Native()) == "gcc"
    assert default.compiler(arm64) == "aarch64-linux-gnu-gcc"


@pytest.fixture
def arc():
    return Architecture("arc")


class TestArcGcc:
    def test_image_gcc_12(self, arc):
        gcc_12 = Toolchain("gcc-12")
        assert gcc_12.get_image(arc) == "tuxmake/arc_gcc-12"

    def test_image_gcc_13(self, arc):
        gcc_13 = Toolchain("gcc-13")
        assert gcc_13.get_image(arc) == "tuxmake/arc_gcc-13"

    def test_image_gcc_14(self, arc):
        gcc_14 = Toolchain("gcc-14")
        assert gcc_14.get_image(arc) == "tuxmake/arc_gcc-14"

    def test_image_gcc_15(self, arc):
        gcc_15 = Toolchain("gcc-15")
        assert gcc_15.get_image(arc) == "tuxmake/arc_gcc-15"

    def test_cross_compile_gcc_8(self, arc):
        gcc_8 = Toolchain("gcc-8")
        makevars = gcc_8.expand_makevars(arc)
        # gcc-8 overrides arc CROSS_COMPILE to arc-elf32- (for old tarball-based containers)
        assert makevars.get("CROSS_COMPILE") == "arc-elf32-"

    def test_cross_compile_gcc_9(self, arc):
        gcc_9 = Toolchain("gcc-9")
        makevars = gcc_9.expand_makevars(arc)
        # gcc-9 overrides arc CROSS_COMPILE to arc-elf32- (for old tarball-based containers)
        assert makevars.get("CROSS_COMPILE") == "arc-elf32-"

    def test_cross_compile_gcc_12(self, arc):
        gcc_12 = Toolchain("gcc-12")
        makevars = gcc_12.expand_makevars(arc)
        # gcc-12 uses default arc CROSS_COMPILE (arc-linux-gnu- from arc.ini)
        assert (
            makevars.get("CROSS_COMPILE") is None or makevars.get("CROSS_COMPILE") == ""
        )

    def test_cross_compile_gcc_13(self, arc):
        gcc_13 = Toolchain("gcc-13")
        makevars = gcc_13.expand_makevars(arc)
        # gcc-13 uses default arc CROSS_COMPILE (arc-linux-gnu- from arc.ini)
        assert (
            makevars.get("CROSS_COMPILE") is None or makevars.get("CROSS_COMPILE") == ""
        )

    def test_cross_compile_gcc_14(self, arc):
        gcc_14 = Toolchain("gcc-14")
        makevars = gcc_14.expand_makevars(arc)
        # gcc-14 uses default arc CROSS_COMPILE (arc-linux-gnu- from arc.ini)
        assert (
            makevars.get("CROSS_COMPILE") is None or makevars.get("CROSS_COMPILE") == ""
        )

    def test_cross_compile_gcc_15(self, arc):
        gcc_15 = Toolchain("gcc-15")
        makevars = gcc_15.expand_makevars(arc)
        # gcc-15 uses default arc CROSS_COMPILE (arc-linux-gnu- from arc.ini)
        assert (
            makevars.get("CROSS_COMPILE") is None or makevars.get("CROSS_COMPILE") == ""
        )
