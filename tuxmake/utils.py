import functools
import os
import subprocess
import shlex
import shutil
import time
import urllib.request
from pathlib import Path
from typing import List

# Constants for file operations
KB = 1024
MB = KB * 1024
DOWNLOAD_CHUNK_SIZE = 2 * MB  # 2MB chunks for download performance
PROGRESS_REPORT_CHUNK_SIZE = 1 * MB  # Report progress every 1MB for responsiveness


def quote_command_line(cmd: List[str], separator: str = " ") -> str:
    return separator.join([shlex.quote(c) for c in cmd])


def get_git_dir(directory):
    # In a git worktree, .git is a file that points at a directory outside
    # the tree. Return that directory, so it can be made available to the
    # build. Return None for a normal tree, where .git is inside it.
    dotgit = directory / ".git"
    if not dotgit.is_file():
        return None
    _, sep, after = dotgit.read_text().partition("gitdir:")
    if not sep:
        return None
    gitdir = directory / Path(after.strip())
    commondir = gitdir / "commondir"
    if commondir.exists():
        gitdir = gitdir / commondir.read_text().strip()
    gitdir = gitdir.resolve()
    if not gitdir.is_dir():
        # The pointer can be stale. Mounting a path that is not there gives
        # the build an empty dir, and then git finds no repo at all.
        return None
    return gitdir


def get_directory_timestamp(directory):
    if (directory / ".git").exists():
        try:
            return subprocess.check_output(
                ["git", "log", "--date=unix", "--format=%cd", "--max-count=1"],
                cwd=str(directory),
                encoding="utf-8",
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(e)

    s = os.stat(directory)
    return str(int(s.st_mtime))


def retry(*exceptions, max_attempts=5, backoff=1):
    def retry_decorator(func):
        @functools.wraps(func)
        def retry_wrapper(*args, **kwargs):
            attempts = 0
            wait = 1
            while True:
                try:
                    ret = func(*args, **kwargs)
                    return ret
                except Exception as e:
                    attempts += 1
                    if type(e) in exceptions and attempts < max_attempts:
                        time.sleep(wait)
                        wait = wait ** (backoff * 2)
                    else:
                        raise

        return retry_wrapper

    return retry_decorator


def download_file_with_progress(url, output_path, logger=None):
    output_path = Path(output_path)

    def log(msg):
        if logger:
            logger(msg)
        else:
            print(msg)

    # Create request with headers
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "tuxmake")
    req.add_header("Accept-Encoding", "identity")  # Disable compression

    log(f"Downloading {url}")

    with urllib.request.urlopen(req) as response:
        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(output_path, "wb") as f:
            while True:
                chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    mb_downloaded = downloaded // MB
                    mb_total = total_size // MB
                    log(f"Progress: {percent:.1f}% ({mb_downloaded}MB/{mb_total}MB)")
                else:
                    mb_downloaded = downloaded // MB
                    log(f"Downloaded: {mb_downloaded}MB")

        if total_size > 0:
            log(f"Download complete: {total_size // MB}MB")


def prepare_file_from_source(src, dest_path, logger=None):
    dest_path = Path(dest_path)

    def log(msg):
        if logger:
            logger(msg)
        else:
            print(msg)

    if src.startswith(("http://", "https://")):
        if src.endswith(".xz"):
            download_path = dest_path.with_suffix(".download")
            download_file_with_progress(src, download_path, logger)
            log(f"Decompressing {download_path} to {dest_path}")
            with open(dest_path, "wb") as f:
                subprocess.run(["unxz", "-c", str(download_path)], stdout=f, check=True)
            download_path.unlink()  # Remove temp file
        else:
            download_file_with_progress(src, dest_path, logger)
    elif src.endswith(".xz"):
        log(f"Decompressing {src} to {dest_path}")
        with open(dest_path, "wb") as f:
            subprocess.run(["unxz", "-c", src], stdout=f, check=True)
    else:
        log(f"Copying {src} to {dest_path}")
        shutil.copy2(src, dest_path)
