# Curated Containers

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
