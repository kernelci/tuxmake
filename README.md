<div align="center">
  <img src="docs/tuxmake_full.svg" alt="TuxMake Logo" width="50%" />
</div>

[![PyPI version](https://badge.fury.io/py/tuxmake.svg)](https://pypi.org/project/tuxmake/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPI - License](https://img.shields.io/pypi/l/tuxmake)](https://github.com/kernelci/tuxmake/blob/master/LICENSE)

[Documentation](https://tuxmake.org/) - [Repository](https://github.com/kernelci/tuxmake) - [Issues](https://github.com/kernelci/tuxmake/issues)

TuxMake, by [Linaro](https://www.linaro.org/), is a command line tool and
Python library that provides portable and repeatable Linux kernel builds across
a variety of architectures, toolchains, kernel configurations, and make
targets. TuxMake is a part of [TuxSuite](https://tuxsuite.com), a suite of
tools and services to help with Linux kernel development.

## Table of Contents
- [About TuxMake](#about-tuxmake)
- [Installing TuxMake](#installing-tuxmake)
- [Using TuxMake](#using-tuxmake)
- [Examples](#examples)
- [Contributing to TuxMake](#contributing-to-tuxmake)

# About TuxMake

Building Linux is easy, right? You just run "make defconfig; make"!

It gets complicated when you want to support the following combinations:

- Architectures (arc, arm, arm64, i386, mips, parisc, powerpc, riscv, s390, sh,
  sparc, x86_64, etc)
- Toolchains (gcc-8, gcc-9, gcc-10, clang-10, clang-11, clang-nightly, etc)
- Configurations (defconfig, distro configs, allmodconfigs, randconfig, etc)
- Targets (kernel image, documentation, selftests, perf, cpupower, etc)
- Build-time validation (coccinelle, sparse checker, etc)

Each of those items requires specific configuration, and supporting all
combinations is difficult. TuxMake seeks to simplify Linux kernel building by
providing a consistent command line interface to each of those combinations
listed above. You specify what to build at the command line, and TuxMake drives
the build for you, doing the same steps the same way every time.

The real power comes from using TuxMake's curated, portable build environments
distributed as Docker/Podman [container images](https://hub.docker.com/u/tuxmake).
When using these versioned and hermetic filesystem images, your team can use
the same exact toolchain(s) across different workstation platforms. Reporting
and reproducing build failures is trivial by sharing TuxMake command lines with
others.

# Installing TuxMake

There are several options for installing TuxMake:

- [From PyPI](docs/install-pypi.md)
- [Debian packages](docs/install-deb.md)
- [RPM packages](docs/install-rpm.md)
- [Run uninstalled](docs/run-uninstalled.md)

# Using TuxMake

To use TuxMake, navigate to a Linux source tree (where you might usually run
`make`), and run `tuxmake`. By default, it will perform a defconfig build on
your native architecture, using a default compiler (`gcc`).

The behavior of the build can be modified with command-line arguments. Run
`tuxmake --help` to see all command-line arguments.

# Examples

Build from current directory:

    $ tuxmake

Build using Podman:

    $ tuxmake --runtime podman

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

Build DTBs on arm64 using podman:

    $ tuxmake -r podman -a arm64 -t gcc-9 dtbs

Incremental builds can be done by reusing a build directory:

    $ tuxmake --build-dir=/path/to/output
    # hack on source ...
    $ tuxmake --build-dir=/path/to/output
    # only rebuilds what is needed

Using configuration files:

    # reads command line options from ~/.config/tuxmake/myconfig
    $ tuxmake @myconfig
    # reads command line options from /tmp/myconfig
    $ tuxmake @/tmp/myconfig

Display all options:

    $ tuxmake --help

# Contributing to TuxMake

See the [Contribution Guidelines](docs/contributing.md) document for details in
how to contribute to TuxMake. Contributors are expected to follow the [TuxMake
Code of Conduct](docs/code-of-conduct.md) (the same adopted in the Linux kernel
community).
