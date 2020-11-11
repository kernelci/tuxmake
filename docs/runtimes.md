# Runtimes

By default, tuxmake will use any toolchains that you have installed on your
system. i.e., if you specify `--toolchain` and `--target-arch`, the appropriate
(cross) compilers must be available locally in your `$PATH`.

Alternatively, tuxmake supports the concept of runtimes. You can think of
runtimes as both an underlying backend to run the actual build commands, as
well as a provider of toolchains. For example, the `docker` runtime will run
your builds in docker containers, using toolchain container images provided by
the tuxmake maintainers. When running a build, the tuxmake docker runtime will
download the container image that provides the selected (cross) toolchain to
build for the selected target architecture.

The following runtimes are available:

## null

The default runtime. Assumes you have any necessary toolchain installed on your
system. If you request a build that requires a (cross) toolchain you don't have
installed locally, the build will just fail.

## docker

The docker runtime. Runs builds in docker containers, using images provided by
the tuxmake maintainers (or the image informed via **-i/--image**). Will
hit the network every time, looking for updated images.

If you want more details on the contents of the images provided by the TuxMake
team, and how they are generated, see the corresponding
[README file](https://gitlab.com/Linaro/tuxmake/-/blob/master/support/docker/README.md)
in the TuxMake repository.

If you want to provide your own images, take into consideration that:

- Every tool needed for the build must be included in the image. This includes,
  but may not be limited to compilers, assemblers/linkers, file compressors
  (`gz`, `xz`, `tar` etc), compiler wrappers (`ccache`), `make`,
  `u-boot-tools`.
- If you only want to provide a custom toolchain, TuxMake provides base images
  that already contain the base tools and can be reused. Look for
  `tuxmake/base-*` [on Dockerhub](https://hub.docker.com/u/tuxmake).

## docker-local

The same as `docker`, but will only use images that you already have locally,
and fail if you try to use a arch/toolchain combination for which you don't
already have an image.


## podman

The podman runtime works exactly like the docker runtime, but calling `podman`
instead of `docker`.


## podman-local

The same as `docker-local`, but using `podman`.
