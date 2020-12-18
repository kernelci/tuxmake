[![Pipeline Status](https://gitlab.com/Linaro/tuxmake/badges/master/pipeline.svg)](https://gitlab.com/Linaro/tuxmake/pipelines)
[![coverage report](https://gitlab.com/Linaro/tuxmake/badges/master/coverage.svg)](https://gitlab.com/Linaro/tuxmake/commits/master)
[![PyPI version](https://badge.fury.io/py/tuxmake.svg)](https://pypi.org/project/tuxmake/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPI - License](https://img.shields.io/pypi/l/tuxmake)](https://gitlab.com/Linaro/tuxmake/blob/master/LICENSE)

TuxMake is a command line tool and Python library that provides portable and
repeatable Linux kernel builds across a variety of architectures, toolchains,
kernel configurations, and make targets.

[[_TOC_]]


# About TuxMake

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
Additional targets can be specified with command line flags, and are
defined in the `tuxmake/target/*.ini` files.

Every step of the build is clearly shown so that there is no mystery or
obfuscation during the build.

TuxMake does not 'fix' any problems in Linux - rather it provides a thin
veneer over the top of the existing Linux source tree to make building Linux
easier. e.g. if a build combination fails in Linux, it should fail the same way
when building with TuxMake.

The resulting build artifacts and metadata are automatically saved in a single
local per-build directory.

Finally, TuxMake strives to be well tested and robust so that developers can
rely on it to save time and make it worth the additional complexity that
another layer of abstraction introduces.

# Installing TuxMake

## Using pip

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

## Running tuxmake from source

If you don't want to or can't install tuxmake, you can run it directly from the
source directory. After getting the sources via git or something else, there is
a `run` script that will do the right think for you: you can either use that
script, or symlink it to a directory in your `PATH`.

```
/path/to/tuxmake/run --help
sudo ln -s /path/to/tuxmake/run /usr/local/bin/tuxmake && tuxmake --help
```

# Using tuxmake

To use tuxmake, navigate to a Linux source tree (where you might usually run
`make`), and run `tuxmake`. By default, it will perform a defconfig build on
your native architecture, using a default compiler (`gcc`).

The behavior of the build can be modified with command-line arguments. Run
`tuxmake --help` to see all command-line arguments.

# Examples

Build from current directory:

    $ tuxmake

Build from specific directory:

    $ tuxmake --directory /path/to/linux

Build an arm64 kernel:

    $ tuxmake --target-arch=arm64

Build an arm64 kernel with gcc-10:

    $ tuxmake --target-arch=arm64 --toolchain=gcc-10

Build an arm64 kernel with clang-10:

    $ tuxmake --target-arch=arm64 --toolchain=clang-10

Build tinyconfig on arm64 with gcc-9:

    $ tuxmake -a arm64 -t gcc-9 -k tinyconfig

Build defconfig with additional config from file:

    $ tuxmake --kconfig-add /path/to/my.config

Build defconfig with additional config from URL:

    $ tuxmake --kconfig-add https://foo.com/my.config

Build defconfig with additional in-tree config:

    $ tuxmake --kconfig-add kvm_guest.config

Build defconfig with additional inline config:

    $ tuxmake --kconfig-add CONFIG_KVM_GUEST=y

Build tinyconfig on arm64 with gcc-9 using docker:

    $ tuxmake -r docker -a arm64 -t gcc-9 -k tinyconfig

Build DTBs on arm64 using docker:

    $ tuxmake -r docker -a arm64 -t gcc-9 dtbs

Incremental builds can be done by reusing a build directory:

    $ tuxmake --build-dir=/path/to/output
    # hack on source ...
    $ tuxmake --build-dir=/path/to/output
    # only rebuilds what is needed

Display all options:

    $ tuxmake --help

# Contributing to tuxmake

See the [contribution guidelines](docs/contributing.md) document for details in how
to contribute to tuxmake. Contributors are expected to follow the
[tuxmake code of conduct](docs/code-of-conduct.md) (the same adopted in the Linux
kernel community).
