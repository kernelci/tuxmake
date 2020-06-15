from pathlib import Path
import os
import subprocess
from urllib.request import urlopen
from tuxmake.arch import Architecture
from tuxmake.output import get_new_output_dir
from tuxmake.exceptions import InvalidTarget


class Build:
    artifacts = []
    output_dir = None


class defaults:
    target_arch = subprocess.check_output(["uname", "-m"], text=True).strip()
    kconfig = ["defconfig"]
    targets = ["config", "kernel"]


def build(
    tree,
    target_arch=defaults.target_arch,
    kconfig=defaults.kconfig,
    targets=defaults.targets,
    output_dir=None,
):
    arch = Architecture(target_arch)

    if output_dir is None:
        output_dir = get_new_output_dir()
    else:
        os.mkdir(output_dir)

    result = Build()
    for target in targets:
        if target == "config":
            config = output_dir / ".config"
            for conf in kconfig:
                if conf.startswith("http://") or conf.startswith("https://"):
                    download = urlopen(conf)
                    with config.open("a") as f:
                        f.write(download.read().decode("utf-8"))
                elif Path(conf).exists():
                    with config.open("a") as f:
                        f.write(Path(conf).read_text())
                else:
                    subprocess.check_call(
                        ["make", "--silent", conf, f"O={output_dir}"], cwd=tree
                    )
        elif target == "kernel":
            kernel = arch.kernel
            subprocess.check_call(
                ["make", "--silent", kernel, f"O={output_dir}"], cwd=tree
            )
        else:
            raise InvalidTarget(f"Unsupported target: {target}")

    result.output_dir = output_dir
    for artifact in arch.artifacts:
        result.artifacts.append(artifact)
    return result
