from pathlib import Path

ERRORS = (
    "compiler lacks",
    "no configuration exists",
    "not found",
    "no such file or directory",
    "no rule to make target",
)


class LogParser:
    def __init__(self):
        self.errors = 0
        self.warnings = 0

    def parse(self, filepath: Path):
        for orig_line in filepath.open("r", errors="ignore"):
            line = orig_line.lower()
            if "error:" in line or any([s in line for s in ERRORS]):
                self.errors += 1
            if "warning:" in line.lower():
                self.warnings += 1
