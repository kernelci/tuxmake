from datetime import timedelta
import os
import shlex
import sys
from tuxmake.arch import Architecture
from tuxmake.toolchain import Toolchain
from tuxmake.build import build
from tuxmake.cmdline import build_parser
from tuxmake.exceptions import TuxMakeException
from tuxmake.runtime import get_runtime
from tuxmake.utils import supported


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
        os.environ["TUXMAKE_IMAGE"] = options.docker_image
        sys.stderr.write("W: --docker-image is deprecated; use --image instead\n")

    if options.image:
        if not options.runtime:
            options.runtime = "docker"
        os.environ["TUXMAKE_IMAGE"] = options.image

    build_args = {
        k: v
        for k, v in options.__dict__.items()
        if v and k not in ["color", "image", "shell"]
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
