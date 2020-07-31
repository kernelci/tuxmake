import os
import pathlib
import pytest
import shutil


from tuxmake.arch import Architecture


if pytest.__version__ < "3.9":

    @pytest.fixture()
    def tmp_path(tmpdir):
        return pathlib.Path(tmpdir)


@pytest.fixture(autouse=True)
def home(mocker, tmp_path):
    h = tmp_path / "HOME"
    os.environ["HOME"] = str(h)
    return h


@pytest.fixture(scope="session")
def linux(tmpdir_factory):
    src = pathlib.Path(__file__).parent / "fakelinux"
    dst = tmpdir_factory.mktemp("source") / "linux"
    shutil.copytree(src, dst)
    return dst


@pytest.fixture(autouse=True, scope="session")
def fake_cross_compilers(tmpdir_factory):
    missing = []
    for a in Architecture.supported():
        arch = Architecture(a)
        binary = arch.makevars["CROSS_COMPILE"] + "gcc"
        if not shutil.which(binary):
            missing.append(binary)
    if missing:
        testbin = tmpdir_factory.mktemp("bin")
        gcc = "/usr/bin/gcc"
        for p in missing:
            os.symlink(gcc, testbin / p)
        os.environ["PATH"] = f"{testbin}:" + os.environ["PATH"]
