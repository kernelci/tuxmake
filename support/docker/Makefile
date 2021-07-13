export PYTHONPATH := $(shell readlink -f $(CURDIR)/../..)
REGISTRY := docker.io/
PROJECT := tuxmake

ANN := echo
ifneq ($(findstring s,$(filter-out --%,$(MAKEFLAGS))),)
  ANN := true
endif

ifeq ($(V), 1)
Q         :=
LOG       :=
ANN       := true
NOSTDOUT  :=
else
Q         := @
LOG       = > log/$@.log 2>&1 || (cat log/$@.log; false)
NOSTDOUT  := > /dev/null
endif

ANN_BUILD := @$(ANN) " BUILD"
ANN_TEST  := @$(ANN) "  TEST"

docker := docker

default: checkconfig all
	@$(MAKE) --silent show

checkconfig:
	@if [ ! -f configure.mk ]; then echo "configure.mk not found; run ./configure first"; false; fi

-include configure.mk
-include configure.local.mk

noop_releases = $(patsubst %, noop-%, $(releases))
publish_releases = $(patsubst %, publish-%, $(releases))
test_releases = $(patsubst %, test-%, $(releases))
publish_multiarch_releases = $(patsubst %, publish-multiarch-%, $(releases))

$(noop_releases):

log:
	mkdir $@

ifneq ($(findstring s,$(filter-out --%,$(MAKEFLAGS))),)
xargs = xargs -r
else
xargs = xargs -r -t
endif

$(publish_releases): publish-%: test-%
	images=$$(./list-images $*); \
	if [ "x$$images" != x ]; then \
	  echo $(patsubst %, $(PROJECT)/%:latest$(TAG), $(shell ./list-images $*)) | \
	    $(xargs) -n 1 $(docker) push; \
	fi

$(test_releases): test-%: Makefile
	  @list="$(patsubst %, test-%, $(shell ./list-images $*))"; if [ -n "$$list" ]; then $(MAKE) $$list; fi

TIMESTAMP = $(shell date +%Y%m%d)

$(publish_multiarch_releases): publish-multiarch-%: noop-%
	@for image in $(shell ./list-images $*); do \
		echo $(PROJECT)/$${image}:$(TIMESTAMP) $$(./get-arch-images $${image}) | \
			$(xargs) $(docker) manifest create; \
		echo $(PROJECT)/$${image}:latest-dev $$(./get-arch-images $${image}) | \
			$(xargs) $(docker) manifest create; \
		echo $(PROJECT)/$${image}:latest $$(./get-arch-images $${image}) | \
			$(xargs) $(docker) manifest create; \
	done
	@echo $(patsubst %, $(PROJECT)/%:$(TIMESTAMP), $(shell ./list-images $*)) | \
		$(xargs) -n 1 $(docker) manifest push
	@echo $(patsubst %, $(PROJECT)/%:latest-dev, $(shell ./list-images $*)) | \
		$(xargs) -n 1 $(docker) manifest push
	@echo $(patsubst %, $(PROJECT)/%:latest, $(shell ./list-images $*)) | \
		$(xargs) -n 1 $(docker) manifest push


test:
	sh test/test_configure.sh
	sh test/test_gitlab_ci.sh

test-images: $(patsubst %, test-%, $(all_images))

SMOKE_ARCH = x86_64 arm64
SMOKE_TOOLCHAINS = gcc gcc-8 gcc-9 gcc-10 gcc-11 clang-11 clang-12 clang-nightly clang-android
SMOKE_IMAGES = $(foreach toolchain,$(SMOKE_TOOLCHAINS),test-$(toolchain) $(foreach arch,$(SMOKE_ARCH),test-$(arch)_$(toolchain)))
smoke-test: test-base-debian10 test-base-debian11 test-base-debiantesting $(SMOKE_IMAGES)

show:
	@$(docker) images $(PROJECT)/\* | sed -e 1d | sort

clean:
	$(RM) configure.mk
	$(RM) -r log/

purge:
	$(docker) image ls --format='{{.Repository}}:{{.Tag}}' $(PROJECT)/\* \
		| xargs $(docker) rmi

dot:
	@(echo "digraph images {"; sed -e '/# dot:/!d; s/^# dot: //' configure.mk; echo "}")

.PHONY: $(all_images) $(releases) $(publish_releases) $(publish_multiarch_releases) test show list clean purge dot

gitlab-ci.yml: gen-gitlab-ci ../../tuxmake/runtime/docker.ini
	+./gen-gitlab-ci > $@ || ($(RM) $@; false)
