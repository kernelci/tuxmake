import pytest
from tuxmake.log import LogParser


class TestLogParser:
    @pytest.mark.parametrize(
        "log,errors,warnings",
        (
            ("compiler-lacks.log", 1, 0),
            ("invalid-config.log", 1, 0),
            ("compiler-not-found.log", 1, 0),
            ("simple.log", 1, 1),
            ("case.log", 3, 3),
            ("no-such-file-or-directory.log", 1, 5),
            ("no-rule-to-make-target.log", 1, 10),
            ("non-utf8.log", 2, 0),
            ("garbage.log", 0, 2),
        ),
    )
    def test_log(self, logs_directory, log, errors, warnings):
        parser = LogParser()
        parser.parse(logs_directory / log)
        assert (parser.errors, parser.warnings) == (errors, warnings)
