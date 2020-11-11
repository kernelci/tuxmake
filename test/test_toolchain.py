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


class TestGcc:
    def test_image(self, gcc, arm64):
        assert gcc.get_image(arm64) == "tuxmake/arm64_gcc"


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


class TestLLVM:
    def test_image_unversioned(self, arm64):
        llvm = Toolchain("llvm")
        assert llvm.get_image(arm64) == "tuxmake/arm64_clang"

    def test_image_versioned(self, arm64):
        llvm = Toolchain("llvm-10")
        assert llvm.get_image(arm64) == "tuxmake/arm64_clang-10"

    def test_compiler_unversioned(self, arm64):
        assert Toolchain("llvm").compiler(arm64) == "clang"

    def test_compiler_versioned(self, arm64):
        assert Toolchain("llvm-10").compiler(arm64) == "clang"
