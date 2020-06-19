import pytest

import tuxmake.exceptions
from tuxmake.arch import Native
from tuxmake.target import Target


@pytest.fixture
def config():
    return Target("config", Native())


def test_unsupported():
    with pytest.raises(tuxmake.exceptions.UnsupportedTarget):
        Target("foobarbaz", Native())


def test_comparison():
    t1 = Target("config", "Native()")
    t2 = Target("config", "Native()")
    assert t1 == t2
    assert t1 in [t2]


class TestConfig:
    def test_name(self, config):
        assert config.name == "config"

    def test___str__(self, config):
        assert str(config) == "config"

    def test_description(self, config):
        assert isinstance(config.description, str)

    def test_artifacts(self, config):
        assert config.artifacts["config"] == ".config"


class TestDebugKernel:
    def test_make_args(self):
        debugkernel = Target("debugkernel", Native())
        assert debugkernel.make_args == ["vmlinux"]


@pytest.fixture
def arch():
    return Native()


class TestKernel:
    def test_gets_kernel_name_from_arch(self, arch):
        kernel = Target("kernel", arch)
        assert kernel.artifacts

    def test_depends_on_config(self, arch):
        kernel = Target("kernel", arch)
        assert kernel.dependencies == ["config"]
