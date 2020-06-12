import os
import subprocess
from tuxmake.arch import Architecture
from tuxmake.output import get_new_output_dir


class Build:
    artifacts = []
    output_dir = None


def build(tree, target_arch=None, targets=["bzImage"], output_dir=None):
    # FIXME move to tuxbuild.arch
    if target_arch is None:
        target_arch = subprocess.check_output(["uname", "-m"], text=True).strip()
    arch = Architecture(target_arch)

    if output_dir is None:
        output_dir = get_new_output_dir()
    else:
        os.mkdir(output_dir)

    # FIXME don't hardcode
    subprocess.check_call(["make", "defconfig", f"O={output_dir}"], cwd=tree)

    result = Build()
    for target in targets:
        subprocess.check_call(["make", target, f"O={output_dir}"], cwd=tree)

    result.output_dir = output_dir
    for artifact in arch.artifacts:
        result.artifacts.append(artifact)
    return result
