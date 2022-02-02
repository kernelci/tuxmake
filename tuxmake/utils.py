import os
import subprocess
import shlex
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
