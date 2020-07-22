# TuxMake docker containers

## Image design

TuxMake provides Docker container images for all of its supported
architecture/toolchain combinations. These images have the following goals:

- Be as small and portable as possible
- Contain the tools required to build kernels, and nothing else.

The images are based on Debian, and organized in three levels:

- Base images: contain very basic utilities that are used by all toolchains,
  for example `make`, tar, file compressors, etc.

- Build images: based on the base images, plus a native toolchain.  e.g.  a
  `x86_64` image will contain the native `x86_64` compilers. There is a
  "default version" for each toolchain, which gets you the version available in
  Debian `stable`. The versioned toolchains are obtained from the Debian
  release that has them available, usually `stable` or `testing` for newer
  versions.

- Cross build images: based on the build images, plus a crossbuild toolchain
  when that's needed (e.g. `clang` is already a cross compiler and you don't
  need this type of images for `clang`).

```mermaid
graph TD
  base --> gcc
  base --> gcc-8
  base --> gcc-N[...]
  base --> clang
  base --> clang-8
  base --> clang-N[...]
  gcc --> arm64_gcc
  gcc --> x86_64_gcc
  gcc-8 --> arm64_gcc-8
  gcc-8 --> x86_64_gcc-8
```

## Build process

- The list of base and build images is specified in [base.in](base.in).
- Before anything, you need to run [`./configure`](configure) to generate the
  list of images to be built.
- The build process is then controlled by [Makefile](Makefile).
  - `make list` will list all the images that can be built.
  - `make show` will list all the images that you have already built.
  - `make test` runs tests for [`configure`](configure).
- The list of achitectures to build cross toolchain images for is provided by
  tuxmake itself, i.e. all architectures defined in tuxmake will make the
  corresponding images be built.
- The dockerfiles are parameterized:
  - Base images are built from [Dockerfile.base](Dockerfile.base).
  - Build and cross build images are built from [Dockerfile.build](Dockerfile.build).
