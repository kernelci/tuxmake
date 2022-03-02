import os
import pathlib
import pytest
import subprocess
import shutil


from tuxmake.arch import Architecture


if pytest.__version__ < "3.9":

    @pytest.fixture()
    def tmp_path(tmpdir):
        return pathlib.Path(tmpdir)


@pytest.fixture(scope="session")
def test_directory():
    return pathlib.Path(__file__).parent


@pytest.fixture(scope="session")
def logs_directory(test_directory):
    return test_directory / "logs"


@pytest.fixture(scope="session", autouse=True)
def session_home(tmpdir_factory):
    os.environ["HOME"] = str(tmpdir_factory.mktemp("HOME"))


@pytest.fixture(autouse=True)
def home(monkeypatch, tmp_path):
    h = tmp_path / "HOME"
    monkeypatch.setenv("HOME", str(h))
    return h


@pytest.fixture(scope="session")
def linux(test_directory, tmpdir_factory):
    src = test_directory / "fakelinux"
    dst = tmpdir_factory.mktemp("source") / "linux"
    shutil.copytree(src, dst)
    subprocess.check_call(["chmod", "-R", "ugo-w", str(dst)])
    return dst


@pytest.fixture
def linux_rw(tmp_path):
    src = pathlib.Path(__file__).parent / "fakelinux"
    dst = tmp_path / "linux"
    shutil.copytree(src, dst)
    subprocess.check_call(["chmod", "-R", "u+w", str(dst)])
    return dst


@pytest.fixture(autouse=True, scope="session")
def fake_cross_compilers(tmpdir_factory):
    missing = {}
    for a in Architecture.supported():
        arch = Architecture(a)
        for tool in ["gcc", "ld"]:
            binary = arch.makevars["CROSS_COMPILE"] + tool
            if not shutil.which(binary):
                missing[binary] = tool
    if missing:
        testbin = tmpdir_factory.mktemp("bin")
        for p, real in missing.items():
            os.symlink(f"/usr/bin/{real}", testbin / p)
        os.environ["PATH"] = f"{testbin}:" + os.environ["PATH"]


@pytest.fixture()
def Popen(mocker):
    _Popen = mocker.patch("subprocess.Popen")
    _Popen.return_value.communicate.return_value = (
        mocker.MagicMock(),
        mocker.MagicMock(),
    )
    return _Popen
