.PHONY: test

ALL_TESTS_PASSED = ======================== All tests passed ========================

all: unit-tests integration-tests docker-build-tests typecheck codespell
	@printf "\033[01;32m$(ALL_TESTS_PASSED)\033[m\n"


unit-tests:
	python3 -m pytest --cov=tuxmake --cov-report=term-missing --cov-fail-under=100

style:
	black --check --diff .
	flake8 .

typecheck:
	mypy tuxmake

codespell:
	find . -name \*.py | xargs codespell

integration-tests:
	sh test/integration/fakelinux.sh

docker-build-tests:
	$(MAKE) -C support/docker test

version = $(shell python3 -c "import tuxmake; print(tuxmake.__version__)")

release:
	@if ! git diff-index --exit-code --quiet HEAD; then git status; echo "Commit all changes before releasing"; false; fi
	git push
	git tag --sign --message="$(version) release" v$(version)
	flit publish
	git push --tags
