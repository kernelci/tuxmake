import argparse
from datetime import timedelta
import os
from pathlib import Path
import shlex
import sys
from tuxmake import __version__
from tuxmake.arch import Architecture
from tuxmake.toolchain import Toolchain
from tuxmake.build import build, supported, defaults
from tuxmake.exceptions import TuxMakeException
from tuxmake.runtime import get_runtime


def key_value(s):
    parts = s.split("=")
    return (parts[0], "=".join(parts[1:]))


def abspath(path):
    return Path(path).absolute()


def build_parser(**kwargs):
    parser = argparse.ArgumentParser(
        prog="tuxmake",
        usage="%(prog)s [OPTIONS] [targets ...]",
        description="TuxMake is a python utility that provides portable and repeatable Linux kernel builds across a variety of architectures, toolchains, kernel configurations, and make targets.",
        add_help=False,
        **kwargs,
    )

    positional = parser.add_argument_group("Positional arguments")
    positional.add_argument(
        "targets",
        nargs="*",
        type=str,
        help=f"Targets to build. If omitted, tuxmake will build  {' + '.join(defaults.targets)}. Supported targets: {', '.join(supported.targets)}.",
    )

    build_input = parser.add_argument_group("Build input options")
    build_input.add_argument(
        "-C",
        "--directory",
        dest="tree",
        default=".",
        help="Tree to build (default: .).",
    )

    build_output = parser.add_argument_group("Output options")
    build_output.add_argument(
        "-o",
        "--output-dir",
        type=abspath,
        default=None,
        help="Output directory for artifacts.",
    )
    build_output.add_argument(
        "-b",
        "--build-dir",
        type=abspath,
        default=None,
        help="Build directory. For incremental builds, specify the same directory on subsequential builds (default: temporary, clean directory).",
    )

    target = parser.add_argument_group("Build output options")
    target.add_argument(
        "-a",
        "--target-arch",
        type=str,
        help=f"Architecture to build the kernel for. Default: host architecture. Supported: {(', '.join(supported.architectures))}.",
    )
    target.add_argument(
        "-k",
        "--kconfig",
        type=str,
        help=f"kconfig to use. Named (defconfig etc), path to a local config file, or URL to config file (default: {defaults.kconfig}).",
    )
    target.add_argument(
        "-K",
        "--kconfig-add",
        type=str,
        action="append",
        help="Extra kconfig fragments, merged on top of the main kconfig from --kconfig. In tree configuration fragment (e.g. `kvm_guest.config`), path to local file, URL, `CONFIG_*=[y|m|n]`, or `# CONFIG_* is not set`. Can be specified multiple times, and will be merged in the order given.",
    )

    buildenv = parser.add_argument_group("Build environment options")
    buildenv.add_argument(
        "-t",
        "--toolchain",
        type=str,
        help=f"Toolchain to use in the build. Default: none (use whatever Linux uses by default). Supported: {', '.join(supported.toolchains)}; request specific versions by appending \"-N\" (e.g. gcc-10, clang-9).",
    )
    buildenv.add_argument(
        "-w",
        "--wrapper",
        type=str,
        help=f"Compiler wrapper to use in the build. Default: none. Supported: {', '.join(supported.wrappers)}. When used with containers, either the wrapper binary must be available in the container image, OR you can pass --wrapper=/path/to/WRAPPER and WRAPPER will be bind mounted in /usr/local/bin inside the container (for this to work WRAPPER needs to be a static binary, or have its shared library dependencies available inside the container).",
    )
    buildenv.add_argument(
        "-e",
        "--environment",
        type=key_value,
        action="append",
        help="Set environment variables for the build. Format: KEY=VALUE .",
    )
    buildenv.add_argument(
        "-j",
        "--jobs",
        type=int,
        help=f"Number of concurrent jobs to run when building (default: {defaults.jobs}).",
    )
    buildenv.add_argument(
        "-r",
        "--runtime",
        help=f"Runtime to use for the builds. By default, builds are run natively on the build host. Supported: {', '.join(supported.runtimes)}.",
    )
    buildenv.add_argument(
        "-i",
        "--docker-image",
        help="Docker image to build with (implies --docker). {toolchain} and {arch} get replaced by the names of the toolchain and architecture selected for the build. Implies --runtime=docker. (default: tuxmake-provided images).",
    )
    buildenv.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Do a verbose build (default: silent build).",
    )
    buildenv.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Quiet build: only errors messages, if any (default: no).",
    )

    info = parser.add_argument_group("Informational options")
    info.add_argument("-h", "--help", action="help", help="Show program help.")
    info.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    info.add_argument(
        "-A",
        "--list-architectures",
        action="store_true",
        help="List supported architectures and exit.",
    )
    info.add_argument(
        "-T",
        "--list-toolchains",
        action="store_true",
        help="List supported toolchains and exit. Combine with --runtime to list toolchains supported by that particular runtime.",
    )
    info.add_argument(
        "-R",
        "--list-runtimes",
        action="store_true",
        help="List supported runtimes and exit.",
    )
    info.add_argument(
        "-p",
        "--print-support-matrix",
        action="store_true",
        help="Print support matrix (architectures x toolchains). Combine with --runtime to list support matrix for that particular runtime.",
    )
    info.add_argument(
        "-c",
        "--color",
        type=str,
        default="auto",
        choices=["always", "never", "auto"],
        help="Control use of colored output. `always` and `never` do what you expect; `auto` (the default) outputs colors when stdout is a tty.",
    )

    debug = parser.add_argument_group("Debugging options")
    debug.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Provides extra output on stderr for debugging tuxmake itself. This output will not appear in the build log.",
    )
    debug.add_argument(
        "-s",
        "--shell",
        action="store_true",
        help="Opens a shell in the runtime after the build, regardless of its result, for debugging.",
    )
    return parser


def main(*argv):
    if not argv:
        argv = tuple(sys.argv[1:])

    env_options = os.getenv("TUXMAKE")
    if env_options:
        argv = tuple(shlex.split(env_options)) + argv

    parser = build_parser()
    options = parser.parse_args(argv)

    if options.color == "always" or (options.color == "auto" and sys.stdout.isatty()):

        def format_yes_no(b, length):
            if b:
                return "\033[32myes\033[m" + " " * (length - 3)
            else:
                return "\033[31mno\033[m" + " " * (length - 2)

    else:

        def format_yes_no(b, length):
            return f"%-{length}s" % (b and "yes" or "no")

    if options.list_architectures:
        for arch in sorted(supported.architectures):
            print(arch)
        return
    elif options.list_toolchains:
        runtime = get_runtime(options.runtime)
        for toolchain in sorted(runtime.toolchains):
            print(toolchain)
        return
    elif options.list_runtimes:
        for runtime in supported.runtimes:
            print(runtime)
        return
    elif options.print_support_matrix:
        runtime = get_runtime(options.runtime)
        architectures = sorted(supported.architectures)
        toolchains = sorted(runtime.toolchains)
        matrix = {}
        for a in architectures:
            matrix[a] = {}
            for t in toolchains:
                matrix[a][t] = runtime.is_supported(Architecture(a), Toolchain(t))
        length_a = max([len(a) for a in architectures])
        length_t = max([len(t) for t in toolchains])
        arch_format = f"%-{length_a}s"
        toolchain_format = f"%-{length_t}s"
        print(" ".join([" " * length_t] + [arch_format % a for a in architectures]))
        for t in toolchains:
            print(
                " ".join(
                    [toolchain_format % t]
                    + [format_yes_no(matrix[a][t], length_a) for a in architectures]
                )
            )

        return

    if options.environment:
        options.environment = dict(options.environment)

    if options.quiet:
        err = open("/dev/null", "w")
    else:
        err = sys.stderr

    if options.docker_image:
        options.runtime = "docker"
        os.environ["TUXMAKE_DOCKER_IMAGE"] = options.docker_image

    build_args = {
        k: v
        for k, v in options.__dict__.items()
        if v and k not in ["color", "docker_image", "shell"]
    }
    try:
        result = build(**build_args, auto_cleanup=(not options.shell))
        if options.shell:
            result.run_cmd(["bash"], interactive=True)
            result.cleanup()
        for target, info in result.status.items():
            duration = timedelta(seconds=info.duration)
            print(f"I: {target}: {info.status} in {duration}", file=err)
        print(f"I: build output in {result.output_dir}", file=err)
        if result.failed:
            sys.exit(2)
    except TuxMakeException as e:
        sys.stderr.write("E: " + str(e) + "\n")
        sys.exit(1)
