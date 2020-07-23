SRC = $(CURDIR)
O ?= $(CURDIR)
ARCH ?= $(shell basename $$(readlink -f $(SRC)/arch/$$(uname -m).mk) .mk)
VERSION := $(shell uname -r)

ifeq ($(LLVM), )
HOSTCC = gcc
else
HOSTCC = clang
endif

ifeq ($(CROSS_COMPILE),)
CC = gcc
else
CC = $(CROSS_COMPILE)gcc
endif

all:

include arch/$(ARCH).mk
ARCHDIRNAME ?= $(ARCH)

.PHONY: config vmlinux $(IMAGE) modules modules_install dtbs dtbs_install

all: vmlinux $(IMAGE)

kernel_version:
	@echo $(VERSION)

define maybefail
	@if [ "$(filter $(1),$(FAIL))" = "$(1)" ]; then echo "Error: target $(FAIL) failed"; exit 1; fi
endef

########################################################################
# final kernel image
#########################################################################
$(IMAGE): $(O)/arch/$(ARCHDIRNAME)/boot/$(IMAGE)
CLEAN += $(O)/arch/$(ARCHDIRNAME)/boot/$(IMAGE)
$(O)/arch/$(ARCHDIRNAME)/boot/$(IMAGE): $(O)/vmlinux
	$(call maybefail,kernel)
	mkdir -p $$(dirname $@)
	$(COMPRESS) < $< > $@ || ($(RM) $@; false)


########################################################################
# debug kernel image
#########################################################################
vmlinux: $(O)/vmlinux
CLEAN += $(O)/vmlinux
$(O)/vmlinux: $(O)/.config
$(O)/vmlinux: vmlinux.c
	$(call maybefail,debugkernel)
	$(CC) -o $@ $<


########################################################################
# modules
#########################################################################
modules: $(O)/modules
CLEAN += $(O)/modules
$(O)/modules: $(O)/vmlinux
	$(call maybefail,modules)
	mkdir -p $@/lib/modules/$(VERSION)/kernel/fs/ext4
	touch    $@/lib/modules/$(VERSION)/kernel/fs/ext4/ext4.ko

modules_install: $(O)/modules
	mkdir -p $(INSTALL_MOD_PATH)
	cp -r $(O)/modules/lib $(INSTALL_MOD_PATH)/


########################################################################
# dtbs
########################################################################
dtbs: $(O)/dtbs
CLEAN += $(O)/dtbs
$(O)/dtbs: $(O)/.config
	$(call maybefail,dtbs)
	mkdir -p $@/hisilicon
	touch    $@/hisilicon/hi6220-hikey.dtb

dtbs_install: $(O)/dtbs
	mkdir -p $(INSTALL_DTBS_PATH)
	cp -r $(O)/dtbs/* $(INSTALL_DTBS_PATH)/


########################################################################
# configuration
########################################################################
config: $(O)/scripts/kconfig/config
CLEAN += $(O)/scripts/kconfig/config
$(O)/scripts/kconfig/config: scripts/kconfig/config.c
	mkdir -p $$(dirname $@)
	$(HOSTCC) -o $@ $<

defconfig: config
	$(call maybefail,defconfig)
	mkdir -p $(O)
	echo 'CONFIG_MODULES=y' > $(O)/.config

olddefconfig: config
	$(call maybefail,olddefconfig)
	test -f $(O)/.config

tinyconfig: config
	$(call maybefail,tinyconfig)
	mkdir -p $(O)
	echo '# CONFIG_MODULES is not set' > $(O)/.config

kvm_guest.config: config
	$(call maybefail,kvm_guest.config)
	echo CONFIG_KVM_GUEST=y >> $(O)/.config


########################################################################
# cleaning
########################################################################
clean:
	$(RM) -rf $(CLEAN)

distclean: clean
	$(RM) $(O)/.config
