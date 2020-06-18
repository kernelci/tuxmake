import argparse
import sys
from tuxmake import __version__
from tuxmake.build import build, defaults
from tuxmake.exceptions import TuxMakeException


def comma_separated(s):
    return s.split(",")


def main(*argv):
    if not argv:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog="tuxmake")

    parser.add_argument(
        "-a",
        "--target-arch",
        type=str,
        help=f"Architecture to build the kernel for (default: {defaults.target_arch})",
    )

    parser.add_argument(
        "-T",
        "--toolchain",
        type=str,
        help=f"Toolchain to use in the build (default: {defaults.toolchain})",
    )

    parser.add_argument(
        "-t",
        "--targets",
        type=comma_separated,
        help=f"Comma-separated list of targets to build (default: {','.join(defaults.targets)})",
    )

    parser.add_argument(
        "-k",
        "--kconfig",
        type=str,
        action="append",
        help=f"kconfig to use. Named (defconfig etc), or URL to config fragment. Can be specified multiple times (default: {', '.join(defaults.kconfig)})",
    )

    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        help=f"Number of concurrent jobs to run when building (default: {defaults.jobs})",
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    parser.add_argument(
        "tree", nargs="?", default=".", help="Tree to build (default: .)"
    )

    options = parser.parse_args(argv)
    build_args = {k: v for k, v in options.__dict__.items() if v}
    try:
        result = build(**build_args)
        for target, info in result.status.items():
            print(f"I: {target}: {info.status} in {info.duration}", file=sys.stderr)
        print(f"I: build output in {result.output_dir}", file=sys.stderr)
        if result.failed:
            sys.exit(2)
    except TuxMakeException as e:
        sys.stderr.write("E: " + str(e) + "\n")
        sys.exit(1)
