SRC = $(CURDIR)
O ?= $(CURDIR)
ARCH ?= $(shell basename $$(readlink -f $(SRC)/arch/$$(uname -m).mk) .mk)
VERSION := $(shell uname -r)

ifeq ($(LLVM), )
HOSTCC = gcc
CC     = $(CROSS_COMPILE)gcc
else
HOSTCC = clang
CC     = clang
endif

CFLAGS += -nostdlib
ifneq ($(CROSS_COMPILE),)
ifneq ($(shell $(CC) --version 2>&1 | head -n1 | grep clang),)
triplet := $(patsubst %-,%,$(CROSS_COMPILE))
CFLAGS += --target=$(triplet)
endif
endif

all:

include arch/$(ARCH).mk
ARCHDIRNAME ?= $(ARCH)

.PHONY: config vmlinux $(IMAGE) modules modules_install dtbs dtbs_install

all: vmlinux $(IMAGE)

kernelversion:
	$(call maybefail,kernelversion)
	@echo $(VERSION)

define maybefail
	@if [ "$(filter $(1),$(FAIL))" = "$(1)" ]; then echo "error: target $(1) failed" >&2; exit 1; fi
	@if [ "$(filter $(1),$(WARN))" = "$(1)" ]; then echo "warning: target $(1) has some issues" >&2; fi
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
# alternative image
########################################################################
ifneq (,$(ALT_IMAGE))
$(ALT_IMAGE): $(O)/arch/$(ARCHDIRNAME)/boot/$(ALT_IMAGE)
CLEAN += $(O)/arch/$(ARCHDIRNAME)/boot/$(ALT_IMAGE)
$(O)/arch/$(ARCHDIRNAME)/boot/$(ALT_IMAGE): $(O)/vmlinux
	$(call maybefail,kernel)
	mkdir -p $$(dirname $@)
	$(ALT_COMPRESS) < $< > $@ || ($(RM) $@; false)
endif


########################################################################
# debug kernel image
#########################################################################
vmlinux: $(O)/vmlinux
CLEAN += $(O)/vmlinux
CLEAN += $(O)/System.map
$(O)/vmlinux: $(O)/.config
$(O)/vmlinux: $(O)/vmlinux.o
	$(call maybefail,debugkernel)
	$(CC) $(CFLAGS) -o $@ $<
	@echo SYSMAP System.map
	@printf "c1000000 T _text\n0000000000000000 D __per_cpu_start\n0000000000000000 D fixed_percpu_data\n" \
		> $(O)/System.map

CLEAN += $(O)/vmlinux.o
$(O)/vmlinux.o: vmlinux.c
	$(CC) $(CFLAGS) -c -o $@ $<

########################################################################
# headers
########################################################################

INSTALL_HDR_PATH ?= ./usr
headers_install:
	mkdir -p $(INSTALL_HDR_PATH)/include/linux
	touch $(INSTALL_HDR_PATH)/include/linux/atomic.h

########################################################################
# XIP kernel image
########################################################################

CLEAN += $(O)/arch/$(ARCHDIRNAME)/boot/xipImage
xipImage: $(O)/arch/$(ARCHDIRNAME)/boot/xipImage
$(O)/arch/$(ARCHDIRNAME)/boot/xipImage: $(O)/vmlinux
	$(call maybefail,xipImage)
	@grep -q CONFIG_XIP_KERNEL=y $(O)/.config || (echo "Error: CONFIG_XIP_KERNEL not set"; false)
	cp $(O)/vmlinux $@


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
DTBSDIR= arch/$(ARCHDIRNAME)/boot/dts
DTBS = $(O)/$(DTBSDIR)
CLEAN += $(DTBS)/hisilicon

$(DTBS): $(DTBSDIR)
	mkdir -p $@

dtbs: $(O)/.config $(DTBS)
	$(call maybefail,dtbs)
	mkdir -p $(DTBS)/hisilicon
	touch    $(DTBS)/hisilicon/hi6220-hikey.dtb

dtbs_install: $(DTBS)
	mkdir -p $(INSTALL_DTBS_PATH)
	cp -r $(DTBS)/* $(INSTALL_DTBS_PATH)/


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

qemu-gdb.config: config
	$(call maybefail,qemu-gdb.config)
	echo CONFIG_DEBUG_INFO=y >> $(O)/.config


########################################################################
# cleaning
########################################################################
clean:
	$(RM) -rf $(CLEAN)

distclean: clean
	$(RM) $(O)/.config
