TuxMake is a thin python+docker wrapper for building Linux kernels.

Python is used to provide a common command-line interface for building across
architectures, targets, and toolchains.

Docker is used to provide isolated build environments, and allows builds to be
reproducible.

Requirements: python 3.6+, docker

[[_TOC_]]

## Goals

Building Linux is easy, right? You just run "make defconfig; make"!

It gets complicated when you want to support the following combinations:
- Architectures (x86, i386, arm64, arm, mips, arc, riscv, powerpc, s390, sparc, etc)
- Toolchains (gcc-8, gcc-9, gcc-10, clang-8, clang-9, clang-10, etc)
- Configurations (defconfig, distro configs, allmodconfigs, randconfig, etc)
- Targets (kernel image, documentation, selftests, perf, cpupower, etc)
- Build-time validation (coccinelle, sparse checker, etc)

Each of those items requires specific configuration, and supporting all
combinations becomes difficult. TuxMake seeks to simplify Linux kernel building
by supporting dockerized build environments and providing a consistent command
line interface to each of those combinations listed above.

For example, wouldn't it be great if a user could install docker and then check
out a Linux source tree and run:

```sh
tuxmake --kconfig defconfig --target-arch arm64 --toolchain clang-9
```

While bit-for-bit [reproducible
builds](https://www.kernel.org/doc/html/latest/kbuild/reproducible-builds.html)
are out of scope for the initial version of this project, the above command
should be portable such that if there is a problem with the build, any other
user should be able to use the same command to produce the same build problem.

Such an interface provides portability and simplicity, making arbitrary Linux
kernel build combinations easier for developers.

TuxMake should provide strong defaults, making the easy cases easy. By default,
tuxmake will build a config, a kernel, and modules and dtbs if applicable.
Additional targets can be specified with command line flags.

Every step of the build should be clearly shown so that there is no mystery or
obfuscation during the build.

It should not 'fix' any problems in Linux - rather it should provide a thin
veneer over the top of the existing Linux source tree to make building Linux
easier. e.g. if a build combination fails in Linux, it should fail the same way
when building with TuxMake.

The resulting build artifacts and meta-data should be automatically saved in a
single local per-build directory.

Finally, TuxMake must be well tested and reliable so that developers can rely
on it to save time and make it worth the additional complexity that another
layer of abstraction introduces.

## Use Cases

For each use-case shown, an example tuxmake invocation is shown, followed by
the example set of docker commands that would need to be run to complete the
build request.

Note that artifact handling is not dealt with here.

### x86 with defconfig

```sh
tuxmake --kconfig defconfig --target-arch x86 --toolchain gcc-9
```

```sh
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux -it tuxbuild/build-gcc-9_x86 make defconfig
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux -it tuxbuild/build-gcc-9_x86 make -j8
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux -it tuxbuild/build-gcc-9_x86 make -j8 modules
```

### arm64 crossbuild from x86 host

```sh
tuxmake --kconfig defconfig --target-arch arm64 --toolchain gcc-9
```

```sh
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm64 --env CROSS_COMPILE=aarch64-linux-gnu- -it tuxbuild/build-gcc-9_arm64 make -j8 defconfig
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm64 --env CROSS_COMPILE=aarch64-linux-gnu- -it tuxbuild/build-gcc-9_arm64 make -j8 Image
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm64 --env CROSS_COMPILE=aarch64-linux-gnu- -it tuxbuild/build-gcc-9_arm64 make -j8 modules
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm64 --env CROSS_COMPILE=aarch64-linux-gnu- -it tuxbuild/build-gcc-9_arm64 make -j8 dtbs
```

### x86 defconfig with clang

```sh
tuxmake --kconfig defconfig --target-arch x86 --toolchain clang-9
```

```sh
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env CC=clang --env HOSTCC=clang -it tuxbuild/build-clang-9 make defconfig
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env CC=clang --env HOSTCC=clang -it tuxbuild/build-clang-9 make -j8
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env CC=clang --env HOSTCC=clang -it tuxbuild/build-clang-9 make -j8 modules
```

### arm32 crossbuild from x86 host using clang

```sh
tuxmake --kconfig multi_v7_defconfig --target-arch arm --toolchain clang-9
```

```sh
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm --env CC=clang --env HOSTCC=clang --env CROSS_COMPILE=arm-linux-gnueabihf- -it tuxbuild/build-clang-9_arm64 make -j8 multi_v7_defconfig
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm --env CC=clang --env HOSTCC=clang --env CROSS_COMPILE=arm-linux-gnueabihf- -it tuxbuild/build-clang-9_arm64 make -j8 zImage
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm --env CC=clang --env HOSTCC=clang --env CROSS_COMPILE=arm-linux-gnueabihf- -it tuxbuild/build-clang-9_arm64 make -j8 modules
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm --env CC=clang --env HOSTCC=clang --env CROSS_COMPILE=arm-linux-gnueabihf- -it tuxbuild/build-clang-9_arm64 make -j8 dtbs
```

## Build Stages

### Create Config

Required.

Every build must have a `.config`. If a `.config` is provided, it must be
updated with `make olddefconfig`. If a config is not provided, a config can be
built from the source tree using defconfig files, special make targets, and/or
config fragments.

IN: Config arguments

OUT: config file

### Build Kernel

Required.

Building the actual kernel has different make targets depending on architecture
as well as different output kernel types/filenames.

In addition to the kernel binary, other artifacts might include a debug kernel
image and kernel header files.

IN: config file

OUT: kernel image file

### Build Modules

Optional.

When a .config file requests "MODULES", modules might be built.

IN:

OUT: modules.tgz


### Build DTBs

Optional.

Some architectures allow DTBs to be built.

IN:

OUT: Directory tree of `.dtb` files


### Build Perf

Optional.

The `tools/perf` directory might be built.

IN:

OUT: perf binaries

### Build selftests

Optional.

The `tools/testing/selftests` directory might be built.

IN:

OUT: kselftest artifacts

### Build Documentation

Optional.

The `Documentation` directory might be built.

IN:

OUT: documentation artifacts

## Build Artifacts

Each build stage will produce artifacts. Some artifacts (like `.config`) need
to be passed to subsequent build stages. All artifacts should be preserved in a
local per-build directory.

Build artifacts will be saved to a path defined by `KBUILD_OUTPUT`, if set.

Things like modules need to be installed with `make modules_install` into the
build directory.

## Other Variables

`KBUILD_BUILD_USER`, `KBUILD_BUILD_HOST`, and `KBUILD_BUILD_TIMESTAMP` may be
set to define information about the build environment. These values are built
into the kernel, so to have truly reproducible builds, they should be set
consistently/statically.

Passing `-s` to make will make the build quieter by eliminating output except
for error output.

Passing `-k` to make will the build keep going after failure, which is often
desirable.

## Future Work

The following features are desirable and should be possible to do with TuxMake.

- Support additional native build architectures (such as arm64) and cross build
  combinations
- Support additional targets in the kernel source tree
- Support additional build-time validation

