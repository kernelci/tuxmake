import subprocess
from tuxmake.arch import Native


class TestNative:
    def test_machine_name(self):
        m = subprocess.check_output(["uname", "-m"]).strip().decode("ascii")
        assert Native().name == m
