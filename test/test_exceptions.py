from tuxmake.exceptions import UnsupportedTarget
from tuxmake.exceptions import UnsupportedArchitecture
from tuxmake.exceptions import UnsupportedToolchain


def test_unsupported_target():
    assert "Unsupported target: foo" in str(UnsupportedTarget("foo"))


def test_unsupported_architecture():
    assert "Unsupported architecture: foo" in str(UnsupportedArchitecture("foo"))


def test_unsupported_toolchain():
    assert "Unsupported toolchain: foo" in str(UnsupportedToolchain("foo"))
