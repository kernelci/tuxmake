O ?= $(CURDIR)
ARCH := $(shell uname -m)
VERSION := $(shell uname -r)

all:

include arch/$(ARCH).mk
ARCHDIRNAME ?= $(ARCH)

.PHONY: vmlinux $(IMAGE) modules modules_install dtbs dtbs_install

all: vmlinux $(IMAGE)

kernel_version:
	@echo $(VERSION)

define maybefail
	@if [ "$(filter $(1),$(FAIL))" = "$(1)" ]; then echo "Error: target $(FAIL) failed"; exit 1; fi
endef

$(IMAGE): $(O)/arch/$(ARCHDIRNAME)/boot/$(IMAGE)

vmlinux: $(O)/vmlinux

modules: $(O)/modules

dtbs: $(O)/dtbs

$(O)/arch/$(ARCHDIRNAME)/boot/$(IMAGE): $(O)/vmlinux
	$(call maybefail,kernel)
	mkdir -p $$(dirname $@)
	touch $@

$(O)/vmlinux: $(O)/.config
	$(call maybefail,debugkernel)
	touch $@

$(O)/modules: $(O)/vmlinux
	$(call maybefail,modules)
	mkdir -p $@/lib/modules/$(VERSION)/kernel/fs/ext4
	touch    $@/lib/modules/$(VERSION)/kernel/fs/ext4/ext4.ko

modules_install: $(O)/modules
	mkdir -p $(INSTALL_MOD_PATH)
	cp -r $(O)/modules/lib $(INSTALL_MOD_PATH)/

$(O)/dtbs: $(O)/.config
	$(call maybefail,dtbs)
	mkdir -p $@/hisilicon
	touch    $@/hisilicon/hi6220-hikey.dtb

dtbs_install: $(O)/dtbs
	mkdir -p $(INSTALL_DTBS_PATH)
	cp -r $(O)/dtbs/* $(INSTALL_DTBS_PATH)/

defconfig:
	$(call maybefail,defconfig)
	mkdir -p $(O)
	echo 'CONFIG_MODULES=y' > $(O)/.config

olddefconfig:
	$(call maybefail,olddefconfig)
	test -f $(O)/.config

tinyconfig:
	$(call maybefail,tinyconfig)
	mkdir -p $(O)
	echo '# CONFIG_MODULES is not set' > $(O)/.config

kvm_guest.config:
	$(call maybefail,kvm_guest.config)
	echo CONFIG_KVM_GUEST=y >> $(O)/.config

clean:
	$(RM) -rf vmlinux $(IMAGE) $(O)/.config $(O)/modules $(O)/dtbs
