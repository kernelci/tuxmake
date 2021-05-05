import subprocess
import pytest
from tuxmake.arch import Architecture
from tuxmake.arch import Native
from tuxmake.toolchain import Toolchain


class TestNative:
    def test_machine_name(self):
        m = subprocess.check_output(["uname", "-m"]).strip().decode("ascii")
        assert Native() == Architecture(m)


class TestAlias:
    def test_aarch64_is_an_alias_to_arm64(self):
        assert Architecture("aarch64") == Architecture("arm64")

    def test_alias_is_not_listed(self):
        assert "aarch64" not in Architecture.supported()

    def test_amd64_is_an_alias_to_x86_64(self):
        assert Architecture("amd64") == Architecture("x86_64")

    def test_architecture_knows_about_its_aliases(self):
        arch = Architecture("arm64")
        assert arch.aliases == ["aarch64"]


@pytest.fixture
def gcc():
    return Toolchain("gcc")


@pytest.fixture
def clang():
    return Toolchain("clang")


@pytest.fixture
def llvm():
    return Toolchain("llvm")


class TestGetImage:
    def test_build_hexagon_on_base_clang_image(self, gcc, clang, llvm):
        hexagon = Architecture("hexagon")
        assert hexagon.get_image(gcc) is None
        assert hexagon.get_image(clang) == "tuxmake/clang"
        assert hexagon.get_image(llvm) == "tuxmake/clang"

    def test_build_hexagon_on_base_versioned_clang_image(self):
        clang_N = Toolchain("clang-12")
        llvm_N = Toolchain("llvm-12")
        hexagon = Architecture("hexagon")
        assert hexagon.get_image(clang_N) == "tuxmake/clang-12"
        assert hexagon.get_image(llvm_N) == "tuxmake/clang-12"

    def test_arm64_defines_no_specific_image(self, gcc, clang, llvm):
        arm64 = Architecture("arm64")
        assert arm64.get_image(gcc) is None
        assert arm64.get_image(clang) is None
        assert arm64.get_image(llvm) is None
