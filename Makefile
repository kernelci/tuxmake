.PHONY: test

ALL_TESTS_PASSED = ======================== All tests passed ========================

all: unit-tests style integration-tests typechecks codespell
	@printf "\033[01;32m$(ALL_TESTS_PASSED)\033[m\n"


unit-tests:
	python3 -m pytest --cov=tuxmake --cov-report=term-missing

style:
	black --check --diff .
	flake8 .

typechecks:
	mypy tuxmake

codespell:
	find . -name \*.py | xargs codespell

integration-tests:
	sh test/integration/fakelinux.sh
