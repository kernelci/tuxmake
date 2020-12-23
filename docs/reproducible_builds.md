# Reproducible Builds

Typical TuxMake invocations, when using a container runtime (`--runtime`), are
reliable enough and sufficient to reproduce most build errors and warnings.

It is also possible to perform bit-for-bit reproducible builds across systems
and users. To do so, care needs to be taken to guarantee that all build inputs
are reproduced so that the resulting build binaries are also identical.

The Linux kernel provides guidelines on performing reproducible builds which
can be seen at
[kernel.org](https://www.kernel.org/doc/html/latest/kbuild/reproducible-builds.html).

Minimally, the following considerations need to be taken when using TuxMake to
perform reproducible builds.

## Environment Variables

The following environment variables must be set to fixed values.

- `KBUILD_BUILD_TIMESTAMP`
- `KBUILD_BUILD_USER`
- `KBUILD_BUILD_HOST`

## Container Image

TuxMake will by default use the latest container image available. To avoid that
and ensure a specific container image is used, provide it explicitly using
`--image` and specify a specific container sha256 value.

## Example

The following example shows how to provide a specific container image and
environment variable overrides to perform a bit-for-bit reproducible build
using TuxMake.

```
tuxmake --image docker.io/tuxmake/x86_64_gcc@sha256:f8218cbfad8ecf6628fc44db864a402070feb87ff43a880e1409649172d4bc8c -r podman -k tinyconfig -e "KBUILD_BUILD_TIMESTAMP='Tue May 26 16:16:14 2020 -0500'" -e "KBUILD_BUILD_USER=tuxmake" -e "KBUILD_BUILD_HOST=tuxmake"
```

With those considerations in mind, as long as the Linux source code is at the
exact same version, and none of the other reproducible build caveats come into
play, the resulting build binaries will be identical across systems, build
users, and time.
