[TuxMake](https://tuxmake.org) containers can be used with TuxMake, or by
themselves.

For example, to perform a Linux kernel build using TuxMake, `cd` to a Linux
source code repository and run:

```
tuxmake -r podman --target-arch x86_64
```

To perform a similar kernel build without TuxMake, run the following command to
mount in the source tree and perform the requisite `make` commands.

```
podman run --rm -v $(pwd):/work -w /work -it tuxmake/x86_64_gcc-10 sh -c 'make defconfig && make -j8'
```
