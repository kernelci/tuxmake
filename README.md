[![Pipeline Status](https://gitlab.com/Linaro/tuxmake/badges/master/pipeline.svg)](https://gitlab.com/Linaro/tuxmake/pipelines)
[![coverage report](https://gitlab.com/Linaro/tuxmake/badges/master/coverage.svg)](https://gitlab.com/Linaro/tuxmake/commits/master)
[![PyPI version](https://badge.fury.io/py/tuxmake.svg)](https://pypi.org/project/tuxmake/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPI - License](https://img.shields.io/pypi/l/tuxmake)](https://gitlab.com/Linaro/tuxmake/blob/master/LICENSE)

TuxMake is a python utility that provides portable and repeatable Linux kernel
builds across a variety of architectures, toolchains, kernel configurations,
and make targets.

[[_TOC_]]

# Status: Pre-Alpha

TuxMake is still in its initial development phase and does not yet have enough
functionality (or smooth edges) to be generally useful. However, brave users
interested in contributing to the concepts, design, and interfaces are welcome
and encouraged to try tuxmake and send feedback. The best way to provide
feedback is by [opening an
issue](https://gitlab.com/Linaro/tuxmake/-/issues/new?issue) or merge request
(see [CONTRIBUTING](CONTRIBUTING.md)).

# Getting Started

## Install TuxMake

TuxMake requires Python version 3, and is available using pip.

To install tuxmake on your system globally:

```
sudo pip3 install -U tuxmake
```

To install tuxbuild to your home directory at ~/.local/bin:

```
pip3 install -U --user tuxmake
```

To upgrade tuxmake to the latest version, run the same command you ran to
install it.

## Usage

To use tuxmake, navigate to a Linux source tree (where you might usually run
`make`), and run `tuxmake`. By default, it will perform a defconfig build on
your native architecture, using a default compiler (`gcc`).

The behavior of the build can be modified with command-line arguments. Run
`tuxmake --help` to see all command-line arguments.

### Docker Support

When specifying `--toolchain` and `--target-arch`, the appropriate compiler
must be available locally.

Alternatively, tuxmake can use portable build environments provided by docker
containers. If you pass the `--runtime docker` option, tuxmake will download
and use the appropriate docker container image for your choice of target
architecture and toolchain. Each of the build steps will be performed inside
the given docker container as your user, provided docker is installed and your
user is allowed to run containers.

If you want to override the docker container image to use, you can do that with
the `--docker-image=` option.

### Target Support

By default, tuxmake will build all available and applicable targets. To build a
specific target or a subset of targets, provide the desired target(s) as
positional arguments.

For example, to build dtbs, run `tuxmake dtbs`. A list of supported targets is
available by running `tuxmake --help`. Specified targets will automatically run
any prerequisite targets.

### Usage Examples

Use Case                                          | TuxMake Invocation
:-------------------------------------------------|:------------------
Build from current directory                      | `tuxmake`
Build from specific directory                     | `tuxmake --directory /path/to/linux`
Build an arm64 kernel                             | `tuxmake --target-arch=arm64`
Build an arm64 kernel with gcc-10                 | `tuxmake --target-arch=arm64 --toolchain=gcc-10`
Build an arm64 kernel with clang-10               | `tuxmake --target-arch=arm64 --toolchain=clang-10`
Build tinyconfig on arm64 with gcc-9              | `tuxmake -a arm64 -t gcc-9 -k tinyconfig`
Build defconfig with additional config from file  | `tuxmake --kconfig-add /path/to/my.config`
Build defconfig with additional config from URL   | `tuxmake --kconfig-add https://foo.com/my.config`
Build defconfig with additional in-tree config    | `tuxmake --kconfig-add kvm_guest.config`
Build defconfig with additional inline config     | `tuxmake --kconfig-add CONFIG_KVM_GUEST=y`
Build tinyconfig on arm64 with gcc-9 using docker | `tuxmake -r docker -a arm64 -t gcc-9 -k tinyconfig`
Build DTBs on arm64 using docker                  | `tuxmake -r docker -a arm64 -t gcc-9 dtbs`
Display all options                               | `tuxmake --help`

# Original Design

*Note: Below is the original design documentation for tuxmake. Actual
implementation may vary.*

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
by providing a consistent command line interface to each of those combinations
listed above. E.g. the following command builds an arm64 kernel with gcc-9:

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

TuxMake provides strong defaults, making the easy cases easy. By default,
tuxmake will build a config, a kernel, and modules and dtbs if applicable.
Additional targets can be specified with command line flags.

Every step of the build is clearly shown so that there is no mystery or
obfuscation during the build.

TuxMake does not 'fix' any problems in Linux - rather it provides a thin
veneer over the top of the existing Linux source tree to make building Linux
easier. e.g. if a build combination fails in Linux, it should fail the same way
when building with TuxMake.

The resulting build artifacts and meta-data are automatically saved in a
single local per-build directory.

Finally, TuxMake strives to be well tested and reliable so that developers can rely
on it to save time and make it worth the additional complexity that another
layer of abstraction introduces.

## Use Cases

For each use-case shown, an example tuxmake invocation is shown, followed by
the example set of docker commands that would need to be run to complete the
build request.

Note that artifact handling is not dealt with here.

### Default build (run on x86_64)

By default tuxmake will do a defconfig build with the default gcc for the native architecture.

```sh
tuxmake
```

```sh
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux -it tuxbuild/build-gcc-9_x86 make defconfig
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux -it tuxbuild/build-gcc-9_x86 make -j8
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux -it tuxbuild/build-gcc-9_x86 make -j8 modules
```

### x86 with defconfig

```sh
tuxmake --kconfig defconfig --target-arch x86_64 --toolchain gcc-9
```

```sh
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux -it tuxbuild/build-gcc-9_x86 make defconfig
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux -it tuxbuild/build-gcc-9_x86 make -j8
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux -it tuxbuild/build-gcc-9_x86 make -j8 modules
```

### arm64 crossbuild from x86_64 host

```sh
tuxmake --kconfig defconfig --target-arch arm64 --toolchain gcc-9
```

```sh
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm64 --env CROSS_COMPILE=aarch64-linux-gnu- -it tuxbuild/build-gcc-9_arm64 make -j8 defconfig
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm64 --env CROSS_COMPILE=aarch64-linux-gnu- -it tuxbuild/build-gcc-9_arm64 make -j8 Image
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm64 --env CROSS_COMPILE=aarch64-linux-gnu- -it tuxbuild/build-gcc-9_arm64 make -j8 modules
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm64 --env CROSS_COMPILE=aarch64-linux-gnu- -it tuxbuild/build-gcc-9_arm64 make -j8 dtbs
```

### x86_64 defconfig with clang

```sh
tuxmake --kconfig defconfig --target-arch x86_64 --toolchain clang-9
```

```sh
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env CC=clang --env HOSTCC=clang -it tuxbuild/build-clang-9 make defconfig
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env CC=clang --env HOSTCC=clang -it tuxbuild/build-clang-9 make -j8
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env CC=clang --env HOSTCC=clang -it tuxbuild/build-clang-9 make -j8 modules
```

### arm32 crossbuild from x86_64 host using clang

```sh
tuxmake --kconfig multi_v7_defconfig --target-arch arm --toolchain clang-9
```

```sh
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm --env CC=clang --env HOSTCC=clang --env CROSS_COMPILE=arm-linux-gnueabihf- -it tuxbuild/build-clang-9_arm64 make -j8 multi_v7_defconfig
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm --env CC=clang --env HOSTCC=clang --env CROSS_COMPILE=arm-linux-gnueabihf- -it tuxbuild/build-clang-9_arm64 make -j8 zImage
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm --env CC=clang --env HOSTCC=clang --env CROSS_COMPILE=arm-linux-gnueabihf- -it tuxbuild/build-clang-9_arm64 make -j8 modules
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux --env ARCH=arm --env CC=clang --env HOSTCC=clang --env CROSS_COMPILE=arm-linux-gnueabihf- -it tuxbuild/build-clang-9_arm64 make -j8 dtbs
```

### Build documentation (only)

```sh
tuxmake --targets htmldocs
```

```sh
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/linux -w /linux -it tuxbuild/build-htmldocs make htmldocs
```

### Build kernel, selftests, and documentation

```sh
tuxmake --targets kernel,selftests,htmldocs
```

### As a python library

```python
import tuxmake

build = tuxmake.build("/path/to/linux")
for artifact in build.artifacts:
    print(artifact)

doc_build = tuxmake.build("/path/to/linux", targets=[tuxmake.targets.htmldocs])

full_build = tuxmake.build("/path/to/linux", targets=tuxmake.targets.all)
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

## Implementation Details

### Build Artifacts

Each build stage will produce artifacts. Some artifacts (like `.config`) need
to be passed to subsequent build stages. All artifacts should be preserved in a
local per-build directory.

Build artifacts will be saved to a path defined by `KBUILD_OUTPUT`, if set.

Things like modules need to be installed with `make modules_install` into the
build directory.

### Other Variables

`KBUILD_BUILD_USER`, `KBUILD_BUILD_HOST`, and `KBUILD_BUILD_TIMESTAMP` may be
set to define information about the build environment. These values are built
into the kernel, so to have truly reproducible builds, they should be set
consistently/statically.

Passing `-s` to make will make the build quieter by eliminating output except
for error output.

Passing `-k` to make will the build keep going after failure, which is often
desirable.

### Additional Questions and Concerns

#### Config

Kernel config needs to handle a user supplied config, config fragments, and configs that are in tree.

#### make clean

tuxmake will `make clean` by default, and provide a flag to disable it if needed.

#### ccache/sccache

ccache and sccache should be supported, but the details are to be determined.

#### build artifacts

* metadata
  * per-target: pass/fail, artifacts
  * command line to reproduce this build locally
* artifacts
* logs

#### supported make targets

Initially the following targets will be supported:

* config
* kernel (Image zImage debug Image etc)
* modules
* dtb
* headers
* htmldocs
* pdfdocs
* kselftests
* perf
* cpupower

#### Containers

tuxmake needs to provide default containerized environments, but also have the
ability to specify alternative container environments.

## Future Work

The following features are desirable and should be possible to do with TuxMake.

- Support additional native build architectures (such as arm64) and cross build
  combinations
- Support additional targets in the kernel source tree
- Support additional build-time validation

