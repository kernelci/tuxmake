import multiprocessing
import shlex

from tuxmake.arch import Architecture
from tuxmake.target import supported_targets
from tuxmake.toolchain import Toolchain
from tuxmake.runtime import Runtime
from tuxmake.wrapper import Wrapper


class supported:
    architectures = Architecture.supported()
    targets = supported_targets()
    toolchains = Toolchain.supported()
    runtimes = Runtime.supported()
    wrappers = Wrapper.supported()


class defaults:
    kconfig = "defconfig"
    targets = [
        "config",
        "kernel",
        "xipkernel",
        "modules",
        "dtbs",
        "dtbs-legacy",
        "debugkernel",
    ]
    jobs = multiprocessing.cpu_count()


def quote_command_line(cmd):
    return " ".join([shlex.quote(c) for c in cmd])
