from pathlib import Path
from tuxmake.arch import Architecture
from tuxmake.runtime import Runtime
from tuxmake.target import Target
from tuxmake.toolchain import Toolchain
from tuxmake.wrapper import Wrapper

root = Path(__file__).parent.parent


def get_sections(filename):
    doc = root / filename
    return set(
        [
            line.replace("## ", "")
            for line in doc.read_text().splitlines()
            if line.startswith("## ")
        ]
    )


def get_table_rows(filename):
    doc = root / filename
    return set(
        [line.split()[0] for line in doc.read_text().splitlines() if " | " in line][1:]
    )


def check_documented(supported, documented, items_name):
    undocumented = set(supported) - documented
    assert undocumented == set(), f"undocumented {items_name}: {undocumented}"


def check_documented_sections(supported, doc, items_name):
    documented = get_sections(doc)
    check_documented(supported, documented, items_name)


def check_documented_table(supported, doc, items_name):
    documented = get_table_rows(doc)
    check_documented(supported, documented, items_name)


class TestDoc:
    def test_targets(self):
        check_documented_sections(Target.supported(), "docs/targets.md", "targets")

    def test_architectures(self):
        check_documented_table(
            Architecture.supported(), "docs/architectures.md", "architectures"
        )

    def test_toolchains(self):
        check_documented_sections(
            Toolchain.supported(), "docs/toolchains.md", "toolchains"
        )

    def test_runtimes(self):
        check_documented_sections(Runtime.supported(), "docs/runtimes.md", "runtimes")

    def test_wrappers(self):
        check_documented_sections(Wrapper.supported(), "docs/wrappers.md", "wrappers")

    def test_no_packages_page(self):
        """
        /packages/ is reserved for the actual packages in the published website.
        """
        assert not Path("docs/packages.md").exists()
