OS := $(shell sh -c 'eval "$$(grep ^ID= /etc/os-release)"; echo $$ID')
-include scripts/config/$(OS).mk

.PHONY: test tags

ALL_TESTS_PASSED = ======================== All tests passed ========================

all: unit-tests integration-tests docker-build-tests man doc typecheck codespell style
	@printf "\033[01;32m$(ALL_TESTS_PASSED)\033[m\n"


unit-tests:
	python3 -m pytest --cov=tuxmake --cov-report=term-missing --cov-fail-under=100 test

style:
	black --check --diff .
	flake8 .

typecheck:
	mypy tuxmake

codespell:
	codespell \
		--check-filenames \
		--skip '.git,public,dist,*.sw*,*.pyc,tags,*.json,.coverage,htmlcov'

RUN_PARTS ?= run-parts --verbose

integration-tests:
	$(RUN_PARTS) test/integration

integration-tests-docker:
	$(RUN_PARTS) --regex=docker test/integration-slow

docker-build-tests:
	$(MAKE) -C support/docker test

release:
	./scripts/release $(V)

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

tags:
	ctags --exclude=public --exclude=tmp -R

clean:
	$(RM) -r tuxmake.1 cli_options.rst docs/cli.md docs/index.md public/ tags
