export PYTHONPATH := $(shell readlink -f $(CURDIR)/../..)
PROJECT := tuxmake

docker_build := docker build
docker := docker

default: checkconfig all
	@$(MAKE) --silent show

checkconfig:
	@if [ ! -f configure.mk ]; then echo "configure.mk not found; run ./configure first"; false; fi

-include configure.mk

all: $(all_images)
base: $(base_images)
build: $(build_images)
crossbuild: $(crossbuild_images)
gcc_all: $(gcc_images)
clang_all: $(clang_images)
ci: $(ci_images)
daily: $(daily_images)
weekly: $(weekly_images)
monthly: $(monthly_images)
releases = all base build crossbuild gcc_all clang_all ci daily weekly monthly
noop_releases = $(patsubst %, noop-%, $(releases))
publish_releases = $(patsubst %, publish-%, $(releases))
publish_multiarch_releases = $(patsubst %, publish-multiarch-%, $(releases))

$(noop_releases):

LOG = > log/$@.log 2>&1 || (cat log/$@.log; false)

log:
	mkdir $@

ifneq ($(findstring s,$(filter-out --%,$(MAKEFLAGS))),)
xargs = xargs -r
else
xargs = xargs -r -t
endif

$(publish_releases): publish-%: %
	@echo $(patsubst %, $(PROJECT)/%:latest$(TAG), $(shell ./list-images $*)) | \
		$(xargs) -n 1 $(docker) push

$(publish_multiarch_releases): publish-multiarch-%: noop-%
	@for image in $(shell ./list-images $*); do \
		echo $(PROJECT)/$${image}:latest $$(./get-arch-images $${image}) | \
			$(xargs) $(docker) manifest create; \
	done
	@echo $(patsubst %, $(PROJECT)/%:latest, $(shell ./list-images $*)) | \
		$(xargs) -n 1 $(docker) manifest push


test:
	sh test/test_configure.sh

show:
	@docker images $(PROJECT)/\* | sort

list: checkconfig
	@echo base_images = $(base_images)
	@echo build_images = $(build_images)
	@echo crossbuild_images = $(crossbuild_images)
	@echo gcc_all_images = $(gcc_images)
	@echo clang_all_images = $(clang_images)
	@echo all_images = $(all_images)
	@echo daily_images = $(daily_images)
	@echo weekly_images = $(weekly_images)
	@echo monthly_images = $(monthly_images)
	@echo ci_images = $(ci_images)

clean:
	$(RM) configure.mk
	$(RM) -r log/

purge:
	docker image ls --format='{{.Repository}}:{{.Tag}}' $(PROJECT)/\* \
		| xargs docker rmi


.PHONY: $(all_images) $(releases) $(publish_releases) $(publish_multiarch_releases) test show list clean purge
