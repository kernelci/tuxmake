import multiprocessing
from typing import List
from tuxmake.arch import Architecture
from tuxmake.target import supported_targets
from tuxmake.target import Compression
from tuxmake.target import default_compression
from tuxmake.toolchain import Toolchain
from tuxmake.runtime import Runtime
from tuxmake.wrapper import Wrapper


class supported:
    architectures: List[str] = Architecture.supported()
    targets: List[str] = supported_targets()
    toolchains: List[str] = Toolchain.supported()
    runtimes: List[str] = Runtime.supported()
    wrappers: List[str] = Wrapper.supported()
    compression: List[str] = Compression.supported


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
    compression: str = default_compression.name
