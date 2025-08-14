import os
import subprocess
import pytest
from unittest.mock import patch, MagicMock
from tuxmake.utils import get_directory_timestamp
from tuxmake.utils import retry
from tuxmake.utils import download_file_with_progress
from tuxmake.utils import prepare_file_from_source
from tuxmake.utils import quote_command_line
from tuxmake.utils import KB, MB, DOWNLOAD_CHUNK_SIZE


class TestGetDirectoryTimestamp:
    def test_git(self, tmp_path):
        subprocess.check_call(["git", "init"], cwd=tmp_path)
        subprocess.check_call(["git", "config", "user.name", "Foo Bar"], cwd=tmp_path)
        subprocess.check_call(
            ["git", "config", "user.email", "foo@bar.com"], cwd=tmp_path
        )
        (tmp_path / "README.md").write_text("HELLO WORLD")
        subprocess.check_call(["git", "add", "README.md"], cwd=tmp_path)
        new_env = dict(os.environ)
        new_env["GIT_COMMITTER_DATE"] = "2021-05-13 12:00 -0300"
        subprocess.check_call(
            ["git", "commit", "--message=First commit"],
            cwd=tmp_path,
            env=new_env,
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


class TestQuoteCommandLine:
    def test_quote_simple_command(self):
        cmd = ["ls", "-la"]
        result = quote_command_line(cmd)
        assert result == "ls -la"

    def test_quote_command_with_spaces(self):
        cmd = ["cat", "file with spaces.txt"]
        result = quote_command_line(cmd)
        assert result == "cat 'file with spaces.txt'"

    def test_quote_command_with_special_chars(self):
        cmd = ["echo", "hello; rm -rf /"]
        result = quote_command_line(cmd)
        assert result == "echo 'hello; rm -rf /'"

    def test_quote_empty_command(self):
        cmd = []
        result = quote_command_line(cmd)
        assert result == ""


class TestConstants:
    def test_constants_values(self):
        assert KB == 1024
        assert MB == 1024 * 1024
        assert DOWNLOAD_CHUNK_SIZE == 2 * MB
        assert DOWNLOAD_CHUNK_SIZE == 2097152


class TestDownloadFileWithProgress:
    def test_download_file_with_progress_success(self, tmp_path):
        output_path = tmp_path / "test_output.txt"
        test_content = b"test file content"
        logger_calls = []

        def mock_logger(msg):
            logger_calls.append(msg)

        mock_response = MagicMock()
        mock_response.headers.get.return_value = str(len(test_content))
        mock_response.read.side_effect = [test_content, b""]  # First chunk, then empty
        mock_response.__enter__ = lambda x: mock_response
        mock_response.__exit__ = lambda x, y, z, w: None

        with patch("urllib.request.Request") as mock_request, patch(
            "urllib.request.urlopen", return_value=mock_response
        ):
            download_file_with_progress(
                "http://example.com/file.txt", output_path, mock_logger
            )

        assert output_path.read_bytes() == test_content

        assert len(logger_calls) >= 2
        assert "Downloading http://example.com/file.txt" in logger_calls[0]
        assert "Download complete" in logger_calls[-1]

        mock_request.assert_called_once_with("http://example.com/file.txt")
        mock_request.return_value.add_header.assert_any_call("User-Agent", "tuxmake")
        mock_request.return_value.add_header.assert_any_call(
            "Accept-Encoding", "identity"
        )

    def test_download_file_without_content_length(self, tmp_path):
        output_path = tmp_path / "test_output.txt"
        test_content = b"test content without length"
        logger_calls = []

        def mock_logger(msg):
            logger_calls.append(msg)

        mock_response = MagicMock()
        mock_response.headers.get.return_value = "0"
        mock_response.read.side_effect = [test_content, b""]
        mock_response.__enter__ = lambda x: mock_response
        mock_response.__exit__ = lambda x, y, z, w: None

        with patch("urllib.request.Request"), patch(
            "urllib.request.urlopen", return_value=mock_response
        ):
            download_file_with_progress(
                "http://example.com/file.txt", output_path, mock_logger
            )

        assert output_path.read_bytes() == test_content
        assert any("Downloaded:" in call for call in logger_calls)

    def test_download_file_without_logger(self, tmp_path):
        output_path = tmp_path / "test_output.txt"
        test_content = b"test file content"

        mock_response = MagicMock()
        mock_response.headers.get.return_value = str(len(test_content))
        mock_response.read.side_effect = [test_content, b""]
        mock_response.__enter__ = lambda x: mock_response
        mock_response.__exit__ = lambda x, y, z, w: None

        with patch("urllib.request.Request"), patch(
            "urllib.request.urlopen", return_value=mock_response
        ), patch("builtins.print") as mock_print:
            download_file_with_progress("http://example.com/file.txt", output_path)

        assert output_path.read_bytes() == test_content
        mock_print.assert_called()
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Downloading" in call for call in print_calls)


class TestPrepareFileFromSource:
    def test_prepare_local_file(self, tmp_path):
        source_file = tmp_path / "source.txt"
        dest_file = tmp_path / "dest.txt"
        test_content = "test content"
        logger_calls = []

        def mock_logger(msg):
            logger_calls.append(msg)

        source_file.write_text(test_content)

        prepare_file_from_source(str(source_file), dest_file, mock_logger)

        assert dest_file.read_text() == test_content
        assert len(logger_calls) == 1
        assert "Copying" in logger_calls[0]

    def test_prepare_local_xz_file(self, tmp_path):
        source_file = tmp_path / "source.txt.xz"
        dest_file = tmp_path / "dest.txt"
        logger_calls = []

        def mock_logger(msg):
            logger_calls.append(msg)

        test_content = "test content for xz"
        temp_file = tmp_path / "temp.txt"
        temp_file.write_text(test_content)

        subprocess.run(
            ["xz", "-c", str(temp_file)], stdout=open(source_file, "wb"), check=True
        )

        prepare_file_from_source(str(source_file), dest_file, mock_logger)

        assert dest_file.read_text() == test_content
        assert len(logger_calls) == 1
        assert "Decompressing" in logger_calls[0]

    @patch("tuxmake.utils.download_file_with_progress")
    def test_prepare_url_file(self, mock_download, tmp_path):
        dest_file = tmp_path / "dest.txt"
        url = "https://example.com/file.txt"

        prepare_file_from_source(url, dest_file)

        mock_download.assert_called_once_with(url, dest_file, None)

    @patch("tuxmake.utils.download_file_with_progress")
    @patch("subprocess.run")
    def test_prepare_url_xz_file(self, mock_subprocess, mock_download, tmp_path):
        dest_file = tmp_path / "dest.txt"
        url = "https://example.com/file.txt.xz"
        logger_calls = []

        def mock_logger(msg):
            logger_calls.append(msg)

        temp_file = dest_file.with_suffix(".download")
        temp_file.touch()

        prepare_file_from_source(url, dest_file, mock_logger)

        expected_temp = dest_file.with_suffix(".download")
        mock_download.assert_called_once_with(url, expected_temp, mock_logger)

        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0][0]
        assert args[0] == "unxz"
        assert args[1] == "-c"
        assert args[2] == str(expected_temp)

        assert len(logger_calls) == 1
        assert "Decompressing" in logger_calls[0]

    def test_prepare_local_file_without_logger(self, tmp_path):
        source_file = tmp_path / "source.txt"
        dest_file = tmp_path / "dest.txt"
        test_content = "test content"

        source_file.write_text(test_content)

        with patch("builtins.print") as mock_print:
            prepare_file_from_source(str(source_file), dest_file, logger=None)

        assert dest_file.read_text() == test_content
        mock_print.assert_called_once()
        print_call = mock_print.call_args[0][0]
        assert "Copying" in print_call

    def test_prepare_local_xz_file_without_logger(self, tmp_path):
        source_file = tmp_path / "source.txt.xz"
        dest_file = tmp_path / "dest.txt"

        test_content = "test content for xz"
        temp_file = tmp_path / "temp.txt"
        temp_file.write_text(test_content)

        subprocess.run(
            ["xz", "-c", str(temp_file)], stdout=open(source_file, "wb"), check=True
        )

        with patch("builtins.print") as mock_print:
            prepare_file_from_source(str(source_file), dest_file, logger=None)

        assert dest_file.read_text() == test_content
        mock_print.assert_called_once()
        print_call = mock_print.call_args[0][0]
        assert "Decompressing" in print_call
