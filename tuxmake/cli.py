import argparse
import sys
from tuxmake import __version__
from tuxmake.build import build, supported, defaults
from tuxmake.exceptions import TuxMakeException


def comma_separated(s):
    return s.split(",")


def main(*argv):
    if not argv:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="tuxmake",
        usage="%(prog)s [OPTIONS] [tree]",
        description="A think wrapper to build Linux kernels",
        add_help=False,
    )
    parser.add_argument(
        "-C", "--directory", dest="tree", default=".", help="Tree to build (default: .)"
    )

    target = parser.add_argument_group("Build target options")
    target.add_argument(
        "-a",
        "--target-arch",
        type=str,
        help=f"Architecture to build the kernel for. Default: host architecture. Supported: {(', '.join(supported.architectures))}",
    )
    target.add_argument(
        "-t",
        "--targets",
        type=comma_separated,
        help=f"Comma-separated list of targets to build. Default: {','.join(defaults.targets)}. Supported: {', '.join(supported.targets)}",
    )
    target.add_argument(
        "-k",
        "--kconfig",
        type=str,
        action="append",
        help=f"kconfig to use. Named (defconfig etc), path to a local file, or URL to config fragment. Can be specified multiple times (default: {', '.join(defaults.kconfig)})",
    )

    buildenv = parser.add_argument_group("Build environment options")
    buildenv.add_argument(
        "-T",
        "--toolchain",
        type=str,
        help=f"Toolchain to use in the build. Default: none (use whatever Linux uses by default). Supported: {', '.join(supported.toolchains)}; request specific versions by appending \"-N\" (e.g. gcc-10, clang-9).",
    )
    buildenv.add_argument(
        "-j",
        "--jobs",
        type=int,
        help=f"Number of concurrent jobs to run when building (default: {defaults.jobs})",
    )
    buildenv.add_argument(
        "-d",
        "--docker",
        action="store_true",
        help="Do the build using Docker containers (defult: No)",
    )
    buildenv.add_argument(
        "-i",
        "--docker-image",
        help="Docker image to build with (implies --docker). {{toolchain}} and {{arch}} get replaced by the names of the toolchain and architecture selected for the build. (default: tuxmake-provided images)",
    )
    buildenv.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Do a verbose build (default: silent build)",
    )

    info = parser.add_argument_group("Informational options")
    info.add_argument("-h", "--help", action="help", help="Show program help")
    info.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )

    options = parser.parse_args(argv)

    if options.docker_image:
        options.docker = True

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
