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


class TestSourceArch:
    def test_source_arch_x86_64(self):
        arch = Architecture("x86_64")
        assert arch.source_arch == "x86"

    def test_source_arch_i386(self):
        arch = Architecture("i386")
        assert arch.source_arch == "x86"

    def test_source_arch_arm64(self):
        arch = Architecture("arm64")
        assert arch.source_arch == "arm64"

    def test_source_arch_armv5(self):
        arch = Architecture("armv5")
        assert arch.source_arch == "arm"


@pytest.fixture
def gcc():
    return Toolchain("gcc")


@pytest.fixture
def clang():
    return Toolchain("clang")


class TestGetImage:
    def test_build_hexagon_on_base_clang_image(self, gcc, clang):
        hexagon = Architecture("hexagon")
        assert hexagon.get_image(gcc) is None
        assert hexagon.get_image(clang) == "tuxmake/clang"

    def test_build_hexagon_on_base_versioned_clang_image(self):
        clang_N = Toolchain("clang-12")
        hexagon = Architecture("hexagon")
        assert hexagon.get_image(clang_N) == "tuxmake/clang-12"

    def test_arm64_defines_no_specific_image(self, gcc, clang):
        arm64 = Architecture("arm64")
        assert arm64.get_image(gcc) is None
        assert arm64.get_image(clang) is None
