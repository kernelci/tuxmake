import os
import re
import subprocess
import shutil
import pathlib
import pytest
from tuxmake.build import Build
from tuxmake.exceptions import UnsupportedMetadataType
from tuxmake.metadata import Metadata


@pytest.fixture(autouse=True, scope="module")
def home(tmpdir_factory):
    os.environ["HOME"] = str(tmpdir_factory.mktemp("HOME"))


@pytest.fixture(scope="module")
def linux(tmpdir_factory):
    orig = pathlib.Path(__file__).parent / "fakelinux"
    source = tmpdir_factory.mktemp("source")
    _linux = source / "linux"
    shutil.copytree(orig, _linux)
    return _linux


@pytest.fixture(scope="module")
def build(linux):
    subprocess.check_call(["git", "init"], cwd=linux)
    subprocess.check_call(["git", "config", "user.name", "Foo Bar"], cwd=linux)
    subprocess.check_call(["git", "config", "user.email", "foo@bar.com"], cwd=linux)
    subprocess.check_call(["git", "checkout", "-b", "mybranch"], cwd=linux)
    subprocess.check_call(["git", "add", "."], cwd=linux)
    subprocess.check_call(["git", "commit", "--message=Start"], cwd=linux)
    subprocess.check_call(["git", "tag", "v5.4.3"], cwd=linux)
    subprocess.check_call(
        ["git", "remote", "add", "origin", "https://foo.com/linux.git"], cwd=linux
    )
    b = Build(linux, target_arch="arm64")
    b.run()
    return b


class TestMetadata:
    def test_invalid_type(self, mocker):
        m = Metadata("source")
        m.config = {"types": {"foo": "xyz"}}
        with pytest.raises(UnsupportedMetadataType):
            m.__init_config__()


class TestKernelVersion:
    def test_happy_path(self, build):
        assert type(build.metadata["source"]["kernelversion"]) is str


class TestGitMetadata:
    def test_git_describe(self, build):
        assert build.metadata["git"]["git_describe"] == "v5.4.3"

    def test_git_branch(self, build):
        assert build.metadata["git"]["git_branch"] == "mybranch"

    def test_git_commit(self, build):
        assert re.match(r"^[0-9a-f]+$", build.metadata["git"]["git_commit"])

    def test_git_url(self, build):
        assert build.metadata["git"]["git_url"] == "https://foo.com/linux.git"


class TestUname:
    def test_uname(self, build):
        assert sorted(build.metadata["uname"].keys()) == [
            "kernel",
            "kernel_release",
            "kernel_version",
            "machine",
            "operating_system",
        ]


class Compiler:
    @pytest.mark.parametrize("field", ["name", "version", "version_full"])
    def test_compiler(self, build, field):
        assert type(build.metadata["compiler"][field]) is str


class TestOs:
    @pytest.mark.parametrize("field", ["name", "version"])
    def test_os(self, build, field):
        assert type(build.metadata["os"][field]) is str


class TestTools:
    def test_tools(self, build):
        assert type(build.metadata["tools"]) is dict


class TestArtifacts:
    def test_modules(self, build):
        assert len(build.metadata["artifacts"]["modules"]) > 0

    def test_dtbs(self, build):
        assert type(build.metadata["artifacts"]["dtbs"]) is list
