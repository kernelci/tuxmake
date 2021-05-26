# Using TuxMake with custom container images

Even though TuxMake provides a set of curated container images, very few
assumptions are made on the contents of an image: TuxMake only cares that the
necessary tools are included in the image, and available in the default search
path.

## Using a custom container image

When you request the build to use a container image (`--runtime=podman` or
`--runtime=docker`), by default TuxMake will use one of its curated container
images. You can, however, use any image that you would like by just using
`--image` option, or the `TUXMAKE_IMAGE` environment variable.

The only difference when using a custom container image is that you are now
responsible for ensuring that the image has the right tools and packages
necessary to perform the build that you want to do.

## Using an entire set of custom container images

When deciding which image to use, TuxMake can interpolate a few variables such
as the target architecture and toolchain names into the string you passed to
the `--image` option. For example, for gcc builds, the image used by default is
`tuxmake/{arch}\_{toolchain}`. You can use the same expedient to use a custom
set of containers by using something like `--image=foo/bar-{arch}-{toolchain}`
or `export TUXMAKE_IMAGE='foo/bar-{arch}-{toolchain}'`.

The following variables are supported in the interpolation:

Variable | Value
---------|-------
`{arch}` | The selected target architecture (e.g. "x86\_64" or "arm64")
`{toolchain}` | Name of the selected toolchain (e.g. "gcc-10")
`{version_suffix}` | The version suffix from the toolchain name (e.g. "-10")

## Requirements for a custom container image

As said above, TuxMake doesn't care where your image came from, or how it was
put together. All that is needed is that the image has the right set of tools
installed. The first step is ensuring that you have the
[tools listed in the Linux documentation](https://www.kernel.org/doc/html/latest/process/changes.html).
For doing cross builds, you also need the appropriate cross compilers
installed.

Instead of listing each required package, we still instead focus on
how to check what you are missing.

TuxMake has a `--check-environment` option that will, well, check the build
environment for the set of tools known to be needed when build Linux. This
check will run in exact the same environment as specified in the command line,
so for example, if you specify `--runtime=podman --image=mycustomimage`, the
checks will be done under podman, in a container running the `mycustomimage`
image.

For example, to convince yourself that the base Debian image, with no
development tools installed, is not suitable to build Linux, you can run the
following:

```
$ tuxmake --runtime=podman --image=debian --check-environment
tuxmake-check-environment x86_64_gcc
PASS - bash in PATH (`which bash`)
FAIL - bc in PATH (`which bc`)
FAIL - bison in PATH (`which bison`)
FAIL - bzip2 in PATH (`which bzip2`)
FAIL - ccache in PATH (`which ccache`)
FAIL - cpio in PATH (`which cpio`)
FAIL - flex in PATH (`which flex`)
FAIL - git in PATH (`which git`)
PASS - gzip in PATH (`which gzip`)
FAIL - lzop in PATH (`which lzop`)
FAIL - lz4 in PATH (`which lz4`)
FAIL - make in PATH (`which make`)
FAIL - rsync in PATH (`which rsync`)
FAIL - socat in PATH (`which socat`)
PASS - tar in PATH (`which tar`)
FAIL - wget in PATH (`which wget`)
FAIL - xz in PATH (`which xz`)
FAIL - zstd in PATH (`which zstd`)
FAIL - gcc in PATH (`which gcc`)
FAIL - ld in PATH (`which ld`)
FAIL - as in PATH (`which as`)
E: Environment check failed
```

The curated images distributed by TuxMake (which are selected by default if you
don't specify `--image`) are good:


```
$ tuxmake --runtime=podman --check-environment
tuxmake-check-environment x86_64_gcc
PASS - bash in PATH (`which bash`)
PASS - bc in PATH (`which bc`)
PASS - bison in PATH (`which bison`)
PASS - bzip2 in PATH (`which bzip2`)
PASS - ccache in PATH (`which ccache`)
PASS - cpio in PATH (`which cpio`)
PASS - flex in PATH (`which flex`)
PASS - git in PATH (`which git`)
PASS - gzip in PATH (`which gzip`)
PASS - lzop in PATH (`which lzop`)
PASS - lz4 in PATH (`which lz4`)
PASS - make in PATH (`which make`)
PASS - rsync in PATH (`which rsync`)
PASS - socat in PATH (`which socat`)
PASS - tar in PATH (`which tar`)
PASS - wget in PATH (`which wget`)
PASS - xz in PATH (`which xz`)
PASS - zstd in PATH (`which zstd`)
PASS - gcc in PATH (`which gcc`)
PASS - ld in PATH (`which ld`)
PASS - as in PATH (`which as`)
```

To verify the presence of the appropriate cross compiling tools, just specify a
target architecture:

```
$ tuxmake --runtime=podman --target-arch=arm64 --check-environment
tuxmake-check-environment arm64_gcc aarch64-linux-gnu-
PASS - bash in PATH (`which bash`)
PASS - bc in PATH (`which bc`)
PASS - bison in PATH (`which bison`)
PASS - bzip2 in PATH (`which bzip2`)
PASS - ccache in PATH (`which ccache`)
PASS - cpio in PATH (`which cpio`)
PASS - flex in PATH (`which flex`)
PASS - git in PATH (`which git`)
PASS - gzip in PATH (`which gzip`)
PASS - lzop in PATH (`which lzop`)
PASS - lz4 in PATH (`which lz4`)
PASS - make in PATH (`which make`)
PASS - rsync in PATH (`which rsync`)
PASS - socat in PATH (`which socat`)
PASS - tar in PATH (`which tar`)
PASS - wget in PATH (`which wget`)
PASS - xz in PATH (`which xz`)
PASS - zstd in PATH (`which zstd`)
PASS - gcc in PATH (`which gcc`)
PASS - ld in PATH (`which ld`)
PASS - as in PATH (`which as`)
PASS - aarch64-linux-gnu-gcc in PATH (`which aarch64-linux-gnu-gcc`)
PASS - aarch64-linux-gnu-ld in PATH (`which aarch64-linux-gnu-ld`)
PASS - aarch64-linux-gnu-as in PATH (`which aarch64-linux-gnu-as`)
```
