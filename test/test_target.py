import pytest

import tuxmake.exceptions
from tuxmake.arch import Native
from tuxmake.target import Target, Config


@pytest.fixture
def build(mocker):
    b = mocker.MagicMock()
    b.target_arch = Native()
    b.target_overrides = {"kernel": b.target_arch.artifacts["kernel"]}
    b.kconfig = ["defconfig"]
    return b


@pytest.fixture
def config(build):
    return Config("config", build)


def test_unsupported(build):
    with pytest.raises(tuxmake.exceptions.UnsupportedTarget):
        Target("foobarbaz", build)


def test_comparison(build):
    t1 = Target("kernel", build)
    t2 = Target("kernel", build)
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

    def test_does_nothing_if_dot_config_already_exists(self, config, build):
        build.kconfig = "defconfig"
        (build.build_dir / ".config").touch()
        config.prepare()
        assert config.commands == []


class TestDebugKernel:
    def test_commands(self, build):
        debugkernel = Target("debugkernel", build)
        assert debugkernel.commands[0][0] == "xz"
        assert debugkernel.commands[0][-1] == "{build_dir}/vmlinux"


class TestKernel:
    def test_gets_kernel_name_from_arch(self, build):
        kernel = Target("kernel", build)
        assert kernel.artifacts

    def test_depends_on_default(self, build):
        kernel = Target("kernel", build)
        assert kernel.dependencies == ["default"]


class TestModules:
    @pytest.fixture
    def modules(self, build):
        return Target("modules", build)

    def test_install_modules(self, modules):
        assert modules.commands[0][0:2] == ["{make}", "modules_install"]

    def test_strip_modules(self, modules):
        assert "INSTALL_MOD_STRIP=1" in modules.commands[0]

    def test_depends_on_default(self, modules):
        assert modules.dependencies == ["default"]


class TestDtbs:
    def test_commands(self, build):
        dtbs = Target("dtbs", build)
        assert dtbs.commands[0] == ["{make}", "dtbs"]
        assert dtbs.commands[2][1] == "dtbs_install"
        assert "INSTALL_DTBS_PATH=" in dtbs.commands[2][2]

    def test_depends_on_config(self, build):
        dtbs = Target("dtbs", build)
        assert dtbs.dependencies == ["config"]

    def test_artifacts(self, build):
        dtbs = Target("dtbs", build)
        assert dtbs.artifacts["dtbs.tar.xz"] == "dtbs.tar.xz"


class TestDefault:
    def test_command(self, build):
        default = Target("default", build)
        assert default.commands == [["{make}"]]

    def test_depends_on_config(self, build):
        default = Target("default", build)
        assert default.dependencies == ["config"]
