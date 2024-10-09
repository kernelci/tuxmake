# Curated Containers

Both Debian and Fedora containers are maintained for use with TuxMake.

## Debian
TuxMake provides curated [OCI](https://opencontainers.org/) containers for each
of its supported native architecture/target architecture/toolchain
combinations.

These containers represent Debian-based *pristine* Linux kernel build
environments. Notably, they do not contain TuxMake itself; TuxMake merely uses
them to provide what is essentially a chroot environment in which to perform a
build. The containers themselves are reusable and useful without TuxMake
because they're "just" Debian images with all of the Linux kernel build
prerequisites built in.

The containers are defined and built from the
[support/docker](https://gitlab.com/Linaro/tuxmake/-/tree/master/support/docker)
directory in TuxMake's git repository. They are built and published
automatically using a GitLab Pipeline, as defined in TuxMake's
[.gitlab-ci.yml](https://gitlab.com/Linaro/tuxmake/-/blob/master/.gitlab-ci.yml).
The container builds run on a regular schedule.

The full set of TuxMake's containers can be found at
[hub.docker.com/u/tuxmake](https://hub.docker.com/u/tuxmake).

---
**NOTE**

Debian 11 (bullseye) has reached LTS and henceforth only the following architectures will be officially supported:

>  x86_64, arm64, i386, arm

Hence, the [TuxMake containers](https://hub.docker.com/u/tuxmake) will
not be updated from 8th October, 2024 for *gcc-9, gcc-10, clang-11,
clang-12, clang-13 and clang-14* going forward for the targets such as
*armv5, mips, riscv, arc, parisc, powerpc, s390, sh and sparc*
excluding the ones mentioned above. Though the existing containers can
be used in its current form.

---

## Fedora

[CKI project](https://cki-project.org) maintains Fedora containers for use with
TuxMake. These containers are the same ones used for production CKI pipelines,
so they can be used to reproduce CKI pipeline builds.

CKI containers support the following toolchain and architecture combinations for
building the kernel:

|        | x86_64 | aarch64 | ppc64le | s390x |
|--------|--------|---------|---------|-------|
|`gcc`   | yes    | yes     | yes     | yes   |
|`clang` | yes    | yes     | yes     | yes   |
|`llvm`  | yes    | yes     | no      | no    |

Building kernel tools is supported on the following:

|        | x86_64 |
|--------|--------|
|`gcc`   | yes    |
|`clang` | yes    |
|`llvm`  | yes    |

Only the versions of `gcc`, `clang`, and `llvm` provided by Fedora and Fedora
Rawhide are supported.

A stable Fedora image can be used by passing:
```
--image registry.gitlab.com/cki-project/containers/builder-fedora
```
The development Fedora Rawhide image can be used with:
```
--image registry.gitlab.com/cki-project/containers/builder-rawhide
```

The containers are defined in the
[CKI containers repository](https://gitlab.com/cki-project/containers).
