import pytest

import tuxmake.exceptions
from tuxmake.arch import Native
from tuxmake.target import Compression, Target, Config, Kselftest, create_target


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


class TestInstantiateAll:
    @pytest.mark.parametrize("target_name", Target.supported())
    def test_instantiate(self, build, target_name):
        target = Target(target_name, build)
        assert type(target.commands) is list
        assert type(target.artifacts) is dict


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
        assert debugkernel.commands[0][0] == "{z}"
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
        assert modules.commands[1][0:2] == ["{make}", "modules_install"]

    def test_strip_modules(self, modules):
        assert modules.makevars["INSTALL_MOD_STRIP"] == "1"

    def test_depends_on_config(self, modules):
        assert modules.dependencies == ["config"]


class TestDtbs:
    def test_commands(self, build):
        dtbs = Target("dtbs", build)
        assert dtbs.commands[0] == ["{make}", "dtbs"]
        assert dtbs.commands[3][1] == "dtbs_install"
        assert dtbs.makevars["INSTALL_DTBS_PATH"] == "{build_dir}/dtbsinstall/dtbs"

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


class TestTargzPkg:
    def test_wildcards_in_artifacts(self, build, tmp_path):
        filename = "linux-5.13.0-rc2+-x86.tar.gz"
        (tmp_path / filename).touch()

        targzpkg = Target("targz-pkg", build)
        artifacts = targzpkg.find_artifacts(tmp_path)
        assert artifacts[0][0] == filename
        assert artifacts[0][1].name == filename


class TestBinDebPkg:
    def test_multiple_files_against_wildcards(self, build, tmp_path):
        for f in [
            "linux-headers-6.5.0+_6.5.0-11329-g708283abf896-2_arm64.deb",
            "linux-image-6.5.0+_6.5.0-11329-g708283abf896-2_arm64.deb",
            "linux-image-6.5.0+-dbg_6.5.0-11329-g708283abf896-2_arm64.deb",
            "linux-libc-dev_6.5.0-11329-g708283abf896-2_arm64.deb",
            "linux-upstream_6.5.0-rc7-2_arm64.buildinfo",
            "linux-upstream_6.5.0-rc7-2_arm64.changes",
        ]:
            (tmp_path / f).touch()

        bindebpkg = Target("bindeb-pkg", build)
        artifacts = bindebpkg.find_artifacts(tmp_path)
        assert len(artifacts) == 4
        filenames = [f for f, _ in artifacts]
        assert "linux-headers-6.5.0+_6.5.0-11329-g708283abf896-2_arm64.deb" in filenames


class TestKselftest:
    def test_llvm_set_for_clang_toolchain(self, build):
        build.toolchain.name = "clang-20"
        kselftest = Kselftest("kselftest", build)
        assert kselftest.makevars.get("LLVM") == "1"

    def test_llvm_set_for_llvm_toolchain(self, build):
        build.toolchain.name = "llvm"
        kselftest = Kselftest("kselftest", build)
        assert kselftest.makevars.get("LLVM") == "1"

    def test_llvm_not_set_for_gcc_toolchain(self, build):
        build.toolchain.name = "gcc-13"
        kselftest = Kselftest("kselftest", build)
        assert "LLVM" not in kselftest.makevars

    def test_kselftest_bpf_llvm_set_for_clang(self, build):
        build.toolchain.name = "clang-20"
        kselftest_bpf = Kselftest("kselftest-bpf", build)
        assert kselftest_bpf.makevars.get("LLVM") == "1"

    def test_target_factory_returns_kselftest_class(self, build):
        build.toolchain.name = "clang-20"
        kselftest = create_target("kselftest", build)
        assert isinstance(kselftest, Kselftest)
        assert kselftest.makevars.get("LLVM") == "1"


class TestCompression:
    def test_invalid_compression(self):
        with pytest.raises(tuxmake.exceptions.UnsupportedCompression):
            Compression("unexisting")
