import pytest

from tuxmake.arch import Architecture
from tuxmake.toolchain import Toolchain


@pytest.fixture
def gcc():
    return Toolchain("gcc")


@pytest.fixture
def arm64():
    return Architecture("arm64")


class TestGcc:
    def test_docker_image(self, gcc, arm64):
        assert gcc.get_docker_image(arm64) == "tuxmake/arm64_gcc"


@pytest.fixture
def clang():
    return Toolchain("clang")


class TestClang:
    def test_docker_image(self, clang, arm64):
        assert clang.get_docker_image(arm64) == "tuxmake/clang"
