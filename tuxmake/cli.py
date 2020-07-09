import argparse
import sys
from tuxmake import __version__
from tuxmake.build import build, supported, defaults
from tuxmake.exceptions import TuxMakeException


def main(*argv):
    if not argv:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="tuxmake",
        usage="%(prog)s [OPTIONS] [targets ...]",
        description="A thin wrapper to build Linux kernels",
        add_help=False,
    )

    positional = parser.add_argument_group("Positional arguments")
    positional.add_argument(
        "targets",
        nargs="*",
        type=str,
        help=f"Targets to build. If omitted, tuxmake will build  {' + '.join(defaults.targets)}. Supported targets: {', '.join(supported.targets)}",
    )

    build_input = parser.add_argument_group("Build input options")
    build_input.add_argument(
        "-C", "--directory", dest="tree", default=".", help="Tree to build (default: .)"
    )

    target = parser.add_argument_group("Build output options")
    target.add_argument(
        "-a",
        "--target-arch",
        type=str,
        help=f"Architecture to build the kernel for. Default: host architecture. Supported: {(', '.join(supported.architectures))}",
    )
    target.add_argument(
        "-k",
        "--kconfig",
        type=str,
        help=f"kconfig to use. Named (defconfig etc), path to a local config file, or URL to config file (default: {defaults.kconfig})",
    )
    target.add_argument(
        "-K",
        "--kconfig-add",
        type=str,
        action="append",
        help="Extra kconfig fragments, merged on top of the main kconfig from --kconfig. Path to local file, URL, `CONFIG_*=[y|m]`, or `# CONFIG_* is not set`. Can be specified multiple times, and will be merged in the order given",
    )

    buildenv = parser.add_argument_group("Build environment options")
    buildenv.add_argument(
        "-t",
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
        "-r",
        "--runtime",
        help=f"Runtime to use for the builds. By default, builds are run natively on the build host. Supported: {', '.join(supported.runtimes)}",
    )
    buildenv.add_argument(
        "-i",
        "--docker-image",
        help="Docker image to build with (implies --docker). {toolchain} and {arch} get replaced by the names of the toolchain and architecture selected for the build. (default: tuxmake-provided images)",
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
