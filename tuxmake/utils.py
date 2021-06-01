import multiprocessing
import os
import subprocess
import shlex
from typing import List

from tuxmake.arch import Architecture
from tuxmake.target import supported_targets
from tuxmake.toolchain import Toolchain
from tuxmake.runtime import Runtime
from tuxmake.wrapper import Wrapper


class supported:
    architectures: List[str] = Architecture.supported()
    targets: List[str] = supported_targets()
    toolchains: List[str] = Toolchain.supported()
    runtimes: List[str] = Runtime.supported()
    wrappers: List[str] = Wrapper.supported()


class defaults:
    kconfig = "defconfig"
    targets: List[str] = [
        "config",
        "kernel",
        "xipkernel",
        "modules",
        "dtbs",
        "dtbs-legacy",
        "debugkernel",
        "headers",
    ]
    jobs: int = multiprocessing.cpu_count()


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
