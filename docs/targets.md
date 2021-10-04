# Targets

You can think about targets in TuxMake in terms of `make` targets when
building Linux. TuxMake does very little beyond running `make` with the
correct parameters and collecting the resulting artifacts.  TuxMake will not
fix or work around any problems in the Linux build system: if those exist,
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

## default

This target runs `make`. It's an internal target, and is brought in by the
others via dependencies. You usually should not need to build it explicitly,
and if you do you won't get any artifacts out. The artifacts are tied to the
other, specific targets such as `kernel`, `modules`, etc.

## debugkernel

This target builds the debug Kernel image, i.e. `vmlinux`. A compressed copy of
`vmlinux` is stored compressed in the output directory, as `vmlinux.xz`.

## dtbs

This targets builds all DTB files for the selected configuration. The DTBs are
collected in a tarball and copied to the output directory as `dtbs.tar.xz`.

The file structure inside the tarball is not fixed, and depends on the build
(target architecture, etc). When postprocessing it, make sure to look foo all
files inside, regardless of directory depth.

## dtbs-legacy

This target builds all DTB files, like `dtbs`, but does not rely on the
`dtbs_install` target. It's main goal is supporting DTBs in old kernels where
`dtbs_install` didn't exist. It will be skipped on recent kernels.

## kernel

Builds the Kernel image, which is copied into the output directory. The
default kernel image that will be built is architecture-dependent:

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

This can be overridden using the `--kernel-image` option in the [CLI](cli.md)
and the `kernel_image` parameter in the [Python API](python.md).

## targz-pkg

Builds the kernel as a gzip compressed tarball, which is copied to the output
directory. The tarball may include dtbs, modules, the kernel image, and other
files.

## xipkernel

Builds the XIP Kernel image, named `xipImage`, which is then copied into the
output directory. This requires setting `CONFIG_XIP_KERNEL=y` in kconfig, and
is only supported by a few architectures. It will be skipped in most cases.
When this target is built, the `kernel` target is not.

## modules

This target builds the Kernel modules. The modules are compressed in a tarball,
which is copied into the output directory as `modules.tar.xz`.


## headers

This target builds the Kernel headers. The headers are compressed in a tarball.
which is copied into the output directory as `headers.tar.xz`.

## kselftest

Build the kernsel selftests. The resulting, installed tests are compressed in a
tarball which is copied into the output directory as `kselftest.tar.xz`.

TuxMake doesn't do anything special with regards to which tests are built, so
by default it will build everything that kselftest builds by default. If you
want to build a subset of the tests, you can use the same mechanism that you
would use if building Linux by hand: just pass `TARGETS='test1 test2'`in the
command line.

## kselftest-bpf

Build the kernel BPF selftests. These are normally excluded from the kernel
selftests because they require the most recent clang toolchain and a specific
kernel configuration. The resulting, installed tests are compressed in a
tarball which is copied into the output directory as `kselftest-bpf.tar.xz`.

## kselftest-merge

This target merges some configuration required by `kselftest` in the kernel
configuration. It will run after the `config` target. Note that `kselftest`
does not require this, so if you want `kselftest-merge` to be built, it needs
to be specified explicitly. If built, it will always be built before
`kselftest` itself.

## cpupower

This target builds the cpupower program and libraries, from
`tools/power/cpupower`.

## perf

This target builds the perf tool, from `tools/perf`. The resulting artifact is
a tarball named `perf.tar.gz` that can be extracted in a rootfs to provide
`perf`, `trace`, and it plugins.
