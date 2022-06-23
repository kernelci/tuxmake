from pathlib import Path
from typing import Tuple

ERRORS: Tuple[str, ...] = (
    "compiler lacks",
    "no configuration exists",
    "not found",
    "no such file or directory",
    "no rule to make target",
)


class LogParser:
    def __init__(self):
        self.error_list = []
        self.warning_list = []

    @property
    def errors(self):
        return len(self.error_list)

    @property
    def warnings(self):
        return len(self.warning_list)

    def parse(self, filepath: Path) -> None:
        for orig_line in filepath.open("r", errors="ignore"):
            line = orig_line.lower().strip()
            if "error:" in line or any([s in line for s in ERRORS]):
                self.error_list.append(line)
            if "warning:" in line.lower():
                self.warning_list.append(line)
