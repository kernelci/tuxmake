# Reproducible Builds

Starting with version 0.23.0, TuxMake should always, when given the same source
code, the same build options, and a fixed build environment, produce bit by bit
identical artifacts, as described by the
[Reproducible Builds project](https://reproducible-builds.org/).

## Caveats

There are, however, a few caveats. You can only achieve reproducible builds
given a fixed build environment. This includes, but is not limited to:

- Base operating system
- Versions of common tools used in the build: compilers, linkers, etc.
- TuxMake version
- TuxMake build options in the command line

Using one the TuxMake container runtimes (`--runtime-podman` or
`--runtime=docker`) is a good way of achieving a constant build environment,
and users on different host operating systems should be able to reproduce each
other's builds.

## Exceptions

The following artifacts produced by TuxMake are not reproducible:

- `metadata.json`: includes build duration times, information from the build
  machine and operating system, and other details about the local environment
  (e.g. git branch name).
- `build.log`: the generated `make` command lines can be different across
  different machines. Examples:
  - `--jobs=N` depends on the number of cores the build machine has.
  - `O=[...]` depends on the current user's $HOME directory by default.

Everything else should be reproducible, including kernel images, final
configuration, tarballs containing headers/dtbs/modules/kselftest, etc. If
you find any artifact that cannot be reproduced (minus the exceptions
documented above), please send a bug report.

## Paths in the debug info

The build directory and the source tree would otherwise end up in the debug
info, and they are different on every machine. TuxMake maps them away with
`-ffile-prefix-map` in `KCFLAGS` and `KAFLAGS`, and `--remap-path-prefix` in
`KRUSTFLAGS`. The build directory becomes `/tuxmake`, and the source files
get names relative to the tree, the same as an in tree build.

So a debugger does not find the sources on its own. Run it from the root of
the kernel tree, or point it there:

```
(gdb) dir /path/to/linux
```

## Example

Alice does a local arm64 build, using a given kernel configuration.  At the top
of her build log, Alice will see a reproducer command line (the output has been
edited to add a few newlines to improve ieadability):

```
linux (master) $ tuxmake --target-arch arm64 --runtime podman --kconfig tinyconfig
# to reproduce this build locally: tuxmake --target-arch=arm64 --kconfig=tinyconfig \
  --toolchain=gcc --wrapper=ccache --environment=KBUILD_BUILD_TIMESTAMP=@1621270510 \
  --environment=KBUILD_BUILD_USER=tuxmake --environment=KBUILD_BUILD_HOST=tuxmake \
  --runtime=docker --image=docker.io/tuxmake/arm64_gcc \
  config default kernel xipkernel modules dtbs dtbs-legacy debugkernel headers
[...]
```

Now Alice needs her colleague Bob, who is going to help her with testing her
changes, to reproduce that build locally. They sync to make sure they are
working on the same git tree, and Alice shares the above command line with Bob.
Running it on his side, Bob should get a build that is bit by bit identical to
the one Alice did on their side. The only artifact that will be different is
`metadata.json` and `build.log`, because both include data about their local
systems.

## The reproducer script

The same command line is also saved as `reproducer.sh` in the output directory.
It is executable, so person A can just send the file to person B. B runs it
from the root of the same kernel tree:

```
linux (master) $ /path/to/artifacts/reproducer.sh
```

The script does not set up the kernel tree. You have to be in the tree you want
to build.

The reproducer.sh is written before the build starts, so you also get it when
the build fails.

## On container images

As described above, the easiest way of ensuring a consistent build environment
is to the TuxMake container images. However, most of them are rebuilt monthly
at the beginning of the month and sometimes they get rebuilt during the month
if new tools are added to them. There are also nightly images, which are
rebuilt, well, every day.

This means you might have trouble reproducing builds done with the previous
version of a given image, until we have support for generating reproducer
command lines that include the exact image ID.
