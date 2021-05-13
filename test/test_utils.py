import subprocess
from tuxmake.utils import get_directory_timestamp


class TestGetDirectoryTimestamp:
    def test_git(self, tmp_path):
        subprocess.check_call(["git", "init"], cwd=tmp_path)
        subprocess.check_call(["git", "config", "user.name", "Foo Bar"], cwd=tmp_path)
        subprocess.check_call(
            ["git", "config", "user.email", "foo@bar.com"], cwd=tmp_path
        )
        (tmp_path / "README.md").write_text("HELLO WORLD")
        subprocess.check_call(["git", "add", "README.md"], cwd=tmp_path)
        subprocess.check_call(
            ["git", "commit", "--message=First commit"],
            cwd=tmp_path,
            env={"GIT_COMMITTER_DATE": "2021-05-13 12:00 -0300"},
        )
        assert get_directory_timestamp(tmp_path) == "1620918000"

    def test_no_git(self, tmp_path):
        subprocess.check_call(["touch", "-d", "@1620918000", str(tmp_path)])
        assert get_directory_timestamp(tmp_path) == "1620918000"

    def test_git_fails(self, tmp_path, mocker):
        # this will cause git to fail because .git is not a valid gitfile
        subprocess.check_call(["touch", str(tmp_path / ".git")])
        subprocess.check_call(["touch", "-d", "@1620918000", str(tmp_path)])
        assert get_directory_timestamp(tmp_path) == "1620918000"
