export PYTHONPATH := $(shell readlink -f $(CURDIR)/../..)
PROJECT := tuxmake

docker_build := docker build
docker := docker

default: checkconfig all
	@$(MAKE) --silent show

checkconfig:
	@if [ ! -f configure.mk ]; then echo "configure.mk not found; run ./configure first"; false; fi

-include configure.mk

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
	$(MAKE) $(patsubst %, test-%, $(shell ./list-images $*))
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

test-images: $(patsubst %, test-%, $(all_images))

show:
	@docker images $(PROJECT)/\* | sort

clean:
	$(RM) configure.mk
	$(RM) -r log/

purge:
	docker image ls --format='{{.Repository}}:{{.Tag}}' $(PROJECT)/\* \
		| xargs docker rmi


.PHONY: $(all_images) $(releases) $(publish_releases) $(publish_multiarch_releases) test show list clean purge
