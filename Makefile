.PHONY: test

ALL_TESTS_PASSED = ======================== All tests passed ========================

all: unit-tests integration-tests docker-build-tests man doc typecheck codespell style
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
	find . -name \*.md | xargs codespell

integration-tests:
	run-parts --verbose test/integration

integration-tests-docker:
	run-parts --verbose --regex=docker test/integration-slow

docker-build-tests:
	$(MAKE) -C support/docker test

version = $(shell python3 -c "import tuxmake; print(tuxmake.__version__)")

release:
	@if ! git diff-index --exit-code --quiet HEAD; then git status; echo "Commit all changes before releasing"; false; fi
	git push
	git tag --sign --message="$(version) release" v$(version)
	flit publish
	git push --tags

man: tuxmake.1

tuxmake.1: tuxmake.rst cli_options.rst
	rst2man tuxmake.rst $@

cli_options.rst: tuxmake/cli.py scripts/cli2rst.sh
	scripts/cli2rst.sh $@

docs/cli.md: tuxmake.rst tuxmake/cli.py scripts/cli2md.sh
	scripts/cli2md.sh $@

docs/index.md: README.md scripts/readme2index.sh
	scripts/readme2index.sh $@

doc: docs/cli.md docs/index.md
	python3 -m pytest scripts/test_doc.py
	PYTHONPATH=. mkdocs build

clean:
	$(RM) -r tuxmake.1 cli_options.rst docs/cli.md docs/index.md public/
