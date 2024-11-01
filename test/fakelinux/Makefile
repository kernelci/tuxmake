SRC = $(CURDIR)
O ?= $(CURDIR)
ARCH ?= $(shell basename $$(readlink -f $(SRC)/arch/$$(uname -m).mk) .mk)
VERSION := $(shell uname -r)
RELEASE := $(VERSION)+

ifeq ($(LLVM), )
HOSTCC = gcc
CC     = $(CROSS_COMPILE)gcc
LD     = $(CROSS_COMPILE)ld
else
HOSTCC = clang
CC     = clang
LD     = ld.lld
endif

CFLAGS := -nostdlib
ifneq ($(CROSS_COMPILE),)
ifneq ($(shell $(CC) --version 2>&1 | head -n1 | grep clang),)
triplet := $(patsubst %-,%,$(CROSS_COMPILE))
CFLAGS += --target=$(triplet)
endif
endif

KBUILD_BUILD_TIMESTAMP ?= $(shell LANG=C date)
KBUILD_BUILD_USER ?= $(shell whoami)
KBUILD_BUILD_HOST ?= $(shell hostname)

CFLAGS += -DSOURCE_DATE_EPOCH=$(shell date -d "$(KBUILD_BUILD_TIMESTAMP)" +%s)
CFLAGS += -DKBUILD_BUILD_TIMESTAMP='"$(KBUILD_BUILD_TIMESTAMP)"'
CFLAGS += -DKBUILD_BUILD_USER='"$(KBUILD_BUILD_USER)"'
CFLAGS += -DKBUILD_BUILD_HOST='"$(KBUILD_BUILD_HOST)"'

all:

include arch/$(ARCH)/Makefile
ARCHDIRNAME ?= $(ARCH)

.PHONY: config vmlinux $(IMAGE) modules modules_install dtbs dtbs_install targz-pkg

all: vmlinux $(IMAGE)

kernelversion:
	$(call maybefail,kernelversion)
	@echo $(VERSION)

kernelrelease:
	$(call maybefail,kernelrelease)
	@echo $(RELEASE)

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
########################################################################
vmlinux: $(O)/vmlinux
CLEAN += $(O)/vmlinux
CLEAN += $(O)/System.map
$(O)/vmlinux: $(O)/.config
$(O)/vmlinux: $(O)/vmlinux.o
	$(call maybefail,debugkernel)
	$(LD) -o $@ $<
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
$(O)/modules: $(O)/vmlinux $(O)/modules/lib/modules/$(VERSION)/kernel/fs/ext4/ext4.ko
	$(call maybefail,modules)

$(O)/modules/lib/modules/$(VERSION)/kernel/fs/ext4/ext4.ko:
	mkdir -p $(shell dirname $@)
	touch    $@

modules_install: $(O)/modules
	mkdir -p $(INSTALL_MOD_PATH)/lib/modules
	cp -r $(O)/modules/lib/modules/$(VERSION) $(INSTALL_MOD_PATH)/lib/modules/


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

kselftest-merge: config
	$(call maybefail,kselftest-merge)
	echo CONFIG_KSELFTEST_MERGE=y >> $(O)/.config

########################################################################
# targz-pkg: very loosely based on linux/scripts/package/buildtar
########################################################################
KERNELRELEASE = 5.13.0-rc3
tmpdir = $(O)/tar-install
tarball = $(O)/linux-$(KERNELRELEASE)-$(ARCHDIRNAME).tar.gz
dirs = boot
CLEAN += $(tarball)
targz-pkg: all
	mkdir -p -- $(tmpdir)/boot
	cp -v -- $(O)/System.map $(tmpdir)/boot/System.map-$(KERNELRELEASE)
	cp -v -- Kconfig $(tmpdir)/boot/config-$(KERNELRELEASE)
	cp -v -- $(O)/vmlinux $(tmpdir)/boot/vmlinux-$(KERNELRELEASE)
	cp -v -- $(O)/arch/$(ARCHDIRNAME)/boot/$(IMAGE) $(tmpdir)/boot/vmlinuz-$(KERNELRELEASE)

	tar zcf $(tarball) -C $(tmpdir) $(dirs)
	echo "Tarball successfully created in $(tarball)"

########################################################################
# bindeb-pkg: create fake Debian packages like linux does
########################################################################
bindeb-pkg: all
	touch $(O)/../linux-image-$(KERNELRELEASE)_$(KERNELRELEASE)-1_$(ARCH).deb
	touch $(O)/../linux-libc-dev_$(KERNELRELEASE)-1_$(ARCH).deb
	touch $(O)/../linux-libc-dev_$(KERNELRELEASE)-1_$(ARCH).buildinfo
	touch $(O)/../linux-libc-dev_$(KERNELRELEASE)-1_$(ARCH).changes


########################################################################
# cleaning
########################################################################
clean:
	$(RM) -rf $(CLEAN)

distclean: clean
	$(RM) $(O)/.config
