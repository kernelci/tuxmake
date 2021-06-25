.PHONY: test tags dist

export PROJECT := tuxmake

ALL_TESTS_PASSED = ======================== All tests passed ========================

all: typecheck codespell style unit-tests integration-tests docker-build-tests man doc bash_completion
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

RUN_TESTS = scripts/run-tests

integration-tests:
	$(RUN_TESTS) test/integration

integration-tests-docker:
	$(RUN_TESTS) test/integration-slow/docker*

docker-build-tests:
	$(MAKE) -C support/docker test

release:
	./scripts/release $(V)

man: tuxmake.1

tuxmake.1: tuxmake.rst cli_options.rst
	rst2man tuxmake.rst $@

bash_completion: bash_completion/tuxmake

bash_completion/tuxmake: tuxmake/cmdline.py $(wildcard tuxmake/*/*.ini)
	mkdir -p $$(dirname $@)
	python3 -m tuxmake.cmdline bash_completion > $@ || ($(RM) $@; false)

cli_options.rst: tuxmake/cli.py scripts/cli2rst.sh tuxmake/cmdline.py
	scripts/cli2rst.sh $@

docs/cli.md: tuxmake.rst tuxmake/cli.py scripts/cli2md.sh scripts/cli2md.py
	scripts/cli2md.sh $@

docs/index.md: README.md scripts/readme2index.sh
	scripts/readme2index.sh $@

doc: public

public: docs/cli.md docs/index.md $(wildcard docs/*)
	python3 -m pytest scripts/test_doc.py
	PYTHONPATH=. mkdocs build

serve-public: public
	mkdocs serve --livereload --strict

tags:
	ctags --exclude=public --exclude=.mypy_cache --exclude=tmp -R

clean:
	$(RM) -r tuxmake.1 cli_options.rst docs/cli.md docs/index.md public/ tags dist/ bash_completion/

version = $(shell sed -e '/^__version__/ !d; s/"\s*$$//; s/.*"//' tuxmake/__init__.py)

rpm: dist/tuxmake-$(version)-0tuxmake.noarch.rpm

RPMBUILD = rpmbuild
dist/tuxmake-$(version)-0tuxmake.noarch.rpm: dist/tuxmake-$(version).tar.gz dist/tuxmake.spec
	cd dist && \
	$(RPMBUILD) -ta --define "dist tuxmake" --define "_rpmdir $$(pwd)" tuxmake-$(version).tar.gz
	mv $(patsubst dist/%, dist/noarch/%, $@) $@
	rmdir dist/noarch

rpmsrc: dist dist/tuxmake.spec

dist/tuxmake.spec: tuxmake.spec
	cp tuxmake.spec dist/

dist: dist/tuxmake-$(version).tar.gz

dist/tuxmake-$(version).tar.gz:
	flit build

deb: debsrc dist/tuxmake_$(version)-1_all.deb

dist/tuxmake_$(version)-1_all.deb: dist/tuxmake_$(version)-1.dsc
	cd dist/tuxmake-$(version) && dpkg-buildpackage -b -us -uc

debsrc: dist dist/tuxmake_$(version)-1.dsc dist/tuxmake_$(version).orig.tar.gz

dist/tuxmake_$(version).orig.tar.gz: dist/tuxmake-$(version).tar.gz
	ln -f $< $@

dist/tuxmake_$(version)-1.dsc: dist/tuxmake_$(version).orig.tar.gz $(wildcard debian/*)
	cd dist && tar xaf tuxmake_$(version).orig.tar.gz
	cp -r debian/ dist/tuxmake-$(version)
	cd dist/tuxmake-$(version)/ && dpkg-buildpackage -S -d -us -uc
