O ?= $(CURDIR)
ARCH := $(shell uname -m)

all:

include $(ARCH).mk
ARCHDIRNAME ?= $(ARCH)

.PHONY: vmlinux $(IMAGE)

all: vmlinux $(IMAGE)

define maybefail
	@if [ "$(filter $(1),$(FAIL))" = "$(1)" ]; then echo "Error: target $(FAIL) failed"; exit 1; fi
endef

$(IMAGE): $(O)/arch/$(ARCHDIRNAME)/boot/$(IMAGE)

vmlinux: $(O)/vmlinux

$(O)/arch/$(ARCHDIRNAME)/boot/$(IMAGE): $(O)/vmlinux
	$(call maybefail,kernel)
	mkdir -p $$(dirname $@)
	touch $@

$(O)/vmlinux: $(O)/.config
	$(call maybefail,debugkernel)
	touch $@

defconfig:
	$(call maybefail,defconfig)
	mkdir -p $(O)
	touch $(O)/.config

clean:
	$(RM) -rf $(O)/arch/ $(O)/.config
