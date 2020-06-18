.PHONY: test

all: unit-tests style integration-tests

unit-tests:
	python3 -m pytest --cov=tuxmake --cov-report=term-missing

style:
	black --check --diff .
	flake8 .

integration-tests:
	sh test/integration/fakelinux.sh
