# Targets

You can think about targets in TuxMake in terms of `make` targets when
building Linux. TuxMake does very little beyond running `make` with the
correct parameters and collecting the resulting artifacts.  TuxMake will not
fix or work around any problems in the Linux build system: if those exists,
they should be fixed in Linux.

Targets can have dependencies between them. TuxMake ensures that dependencies
are built before the targets that depend on them.

Below we have a description of each of the targets supported by TuxMake.

## config

This target usually does not need to be built explicitly, as most of the other
targets depend on them. However, you can still do a build that only builds
configuration, if you want.

The `config` target is also special in the sense that it implements logic to
compose the final configuration file. See [Kernel configuration
documentation](kconfig.md) for details.

In case you are doing an incremental build and the build directory already
contains a `.config`, this target is skipped.

The final configuration is copied into the output directory as `config`.

## debugkernel

This target builds the debug Kernel image, i.e. `vmlinux`. A compressed copy of
`vmlinux` is stored compressed in the output directory, as `vmlinux.xz`.

## dtbs

This targets builds all DTB files for the selected configuration. The DTBs are
collected in a tarball and copied to the output directory as `dtbs.tar.xz`.

The file structure inside the tarball is not fixed, and depends on the build
(target architecture, etc). When postprocessing it, make sure to look foo all
files inside, regardless of directory depth.

## kernel

Builds the Kernel image, which is copied into the output directory. The
filename is architecture-dependent:

Architecture | Kernel image filename
-------------|-----------------------
aarch64 | Image.gz
amd64 | bzImage
arc | uImage.gz
arm64 | Image.gz
arm | zImage
i386 | bzImage
mips | uImage.gz
riscv | Image.gz
x86_64 | bzImage

## xipkernel

Builds the XIP Kernel image, named `xipImage`, which is then copied into the
output directory. This requires setting `CONFIG_XIP_KERNEL=y` in kconfig, and
is only supported by a few architectures. It will be skipped in most cases.
When this target is built, the `kernel` target is not.

## modules

This target builds the Kernel modules. The modules are compressed in a tarball,
which is copied into the output directory as `modules.tar.gz`.
