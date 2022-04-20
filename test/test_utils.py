import subprocess
import pytest
from tuxmake.utils import get_directory_timestamp
from tuxmake.utils import retry


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


class TestRetry:
    @pytest.fixture(autouse=True)
    def sleep(self, mocker):
        return mocker.patch("time.sleep")

    def test_retry_success_first_time(self, sleep):
        attempts = 0

        @retry()
        def inc():
            nonlocal attempts
            attempts += 1

        inc()
        assert attempts == 1
        assert sleep.call_count == 0

    def test_retry_on_recurring_failure(self, sleep):
        attempts = 0

        @retry(RuntimeError, max_attempts=3)
        def inc():
            nonlocal attempts
            attempts += 1
            raise RuntimeError()

        with pytest.raises(RuntimeError):
            inc()
        assert attempts == 3
        assert sleep.call_count == 2

    def test_retry_success_on_retry(self, sleep):
        attempts = 0

        @retry(RuntimeError, max_attempts=5)
        def inc():
            nonlocal attempts
            attempts += 1
            if attempts <= 2:
                raise RuntimeError()

        inc()
        assert attempts == 3
        assert sleep.call_count == 2
