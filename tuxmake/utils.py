import functools
import os
import subprocess
import shlex
import time
from typing import List


def quote_command_line(cmd: List[str]) -> str:
    return " ".join([shlex.quote(c) for c in cmd])


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
