from datetime import timedelta
import os
import pathlib
import subprocess
import shlex
import sys
import tempfile
from tuxmake import xdg
from tuxmake.logging import set_quiet, info, warning, error
from tuxmake.arch import Architecture
from tuxmake.toolchain import Toolchain
from tuxmake.build import Build
from tuxmake.build_utils import supported
from tuxmake.cmdline import build_parser
from tuxmake.exceptions import TuxMakeException
from tuxmake.runtime import Runtime


def read_config(filename, missing_ok=False):
    configdir = xdg.config_dir()
    path = configdir / filename
    if not path.exists():
        if missing_ok:
            return []
        else:
            error(f"missing configuration file: {path}")
            sys.exit(1)

    res = []
    for line in (configdir / filename).read_text().splitlines():
        if not line.startswith("#"):
            res += shlex.split(line)
    return res


def run_hooks(hooks, cwd):
    if not hooks:
        return
    for hook in hooks:
        try:
            print(hook)
            subprocess.check_call(["sh", "-c", hook], cwd=str(cwd))
        except subprocess.CalledProcessError as e:
            error(f"hook `{hook}` failed with exit code {e.returncode}")
            sys.exit(2)


def main(*origargv):
    if not origargv:
        origargv = tuple(sys.argv[1:])
    argv = read_config("default", missing_ok=True)
    for a in origargv:
        if a.startswith("@"):
            argv += read_config(a[1:])
        else:
            argv.append(a)
    argv = tuple(argv)

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
        runtime = Runtime.get(options.runtime)
        for toolchain in sorted(runtime.toolchains):
            print(toolchain)
        return
    elif options.list_runtimes:
        for runtime in supported.runtimes:
            print(runtime)
        return
    elif options.print_support_matrix:
        runtime = Runtime.get(options.runtime)
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

    set_quiet(options.quiet)

    if options.docker_image:
        os.environ["TUXMAKE_IMAGE"] = options.docker_image
        warning("--docker-image is deprecated; use --image instead")

    if options.image:
        if not options.runtime:
            options.runtime = "docker"
        os.environ["TUXMAKE_IMAGE"] = options.image

    if options.image_registry:
        if not options.runtime:
            options.runtime = "docker"
        os.environ["TUXMAKE_IMAGE_REGISTRY"] = options.image_registry

    if options.targets:
        key_values = [arg for arg in options.targets if "=" in arg]
        for kv in key_values:
            if kv.count("=") > 1:
                error(f"E: invalid KEY=VALUE: {kv}")
                sys.exit(1)
        options.make_variables = dict((arg.split("=") for arg in key_values))
        options.targets = [arg for arg in options.targets if "=" not in arg]

    build_args = {
        k: v
        for k, v in options.__dict__.items()
        if v
        and k
        not in [
            "check_environment",
            "color",
            "docker_image",
            "download_all_korg_gcc_toolchains",
            "image",
            "image_registry",
            "shell",
            "before_hooks",
            "after_hooks",
            "results_hooks",
        ]
    }
    try:
        if options.download_all_korg_gcc_toolchains:
            with tempfile.TemporaryDirectory() as _tmpdir:
                tmpdir = pathlib.Path(_tmpdir)
                build = Build(**build_args, build_dir=tmpdir, output_dir=tmpdir)
                build.download_all_korg_gcc_toolchains()
            return
        if options.check_environment:
            with tempfile.TemporaryDirectory() as _tmpdir:
                tmpdir = pathlib.Path(_tmpdir)
                build = Build(**build_args, build_dir=tmpdir, output_dir=tmpdir)
                build.check_environment()
            return
        build = Build(**build_args, auto_cleanup=(not options.shell))
        run_hooks(options.before_hooks, build.source_tree)
        build.run()
        if options.shell:
            build.run_cmd(["bash"], interactive=True)
            build.cleanup()
        for target, results in build.status.items():
            duration = timedelta(seconds=results.duration)
            info(f"{target}: {results.status} in {duration}")
        info(f"build output in {build.output_dir}")
        if build.failed:
            sys.exit(2)
        else:
            run_hooks(options.after_hooks, build.source_tree)
            run_hooks(options.results_hooks, build.output_dir)
    except TuxMakeException as e:
        error(str(e))
        sys.exit(1)
