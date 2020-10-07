from pathlib import Path
from tuxmake.target import Target


def get_sections(filename):
    root = Path(__file__).parent.parent
    doc = root / filename
    return set(
        [
            line.replace("## ", "")
            for line in doc.read_text().splitlines()
            if line.startswith("## ")
        ]
    )


def check_documented(supported, doc, items_name):
    documented = get_sections(doc)
    undocumented = set(supported) - documented
    assert undocumented == set(), f"undocumented {items_name}: {undocumented}"


class TestDoc:
    def test_targets(self):
        check_documented(Target.supported(), "docs/targets.md", "targets")
