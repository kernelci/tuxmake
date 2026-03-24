# Toolchains

Toolchains can be specified only by their name, or with a version number
attached. For example, `clang` will use whatever `clang` binary you have in
your `$PATH`, while `clang-10` will specifically use `clang` version 10.

## gcc

This toolchain will use `gcc` as compiler. It is the default if you don't
request a specific toolchain. Specify `gcc-N` for requesting specific `gcc`
versions.

## gcc-8

This toolchain uses `gcc-8` as the compiler. It is configured with
`CROSS_COMPILE=arc-elf32-` for the `arc` architecture.

## gcc-9

This toolchain uses `gcc-8` as the compiler. It is configured with
`CROSS_COMPILE=arc-elf32-` for the `arc` architecture.

## clang

This toolchain uses `clang` as compiler, but the GNU binutils tools for
assembling and linking. Specify `clang-N` for specific versions. Special
variants of `clang` are also available:

| Variant | Description |
|---------|-------------|
| `clang-nightly` | Nightly clang builds, updated daily |
| `clang-android` | The exact clang compiler used for official Android builds |

## rustgcc

This toolchain uses `gcc` as C compiler, and also includes the tools required
to build the kernel with [Rust support](https://github.com/Rust-for-Linux).

Alias: `rust`

## rustclang

This toolchain uses `clang` as C compiler, and also includes the tools required
to build the kernel with [Rust support](https://github.com/Rust-for-Linux).

## korg-clang

This toolchain uses `clang` as compiler, but the GNU binutils tools for
assembling and linking. Specify `korg-clang-N` for specific
versions. The toolchain binaries are obtained from
[kernel.org](https://mirrors.edge.kernel.org/pub/tools/llvm/).

## korg-gcc

This toolchain uses `gcc` as compiler. To specify a particular
version, use `korg-gcc-N`, where `N` is >= 8. The toolchain binaries
are obtained from
[kernel.org](https://mirrors.edge.kernel.org/pub/tools/crosstool/).

*__NOTE__*: korg-gcc toolchain is not supported in `null` runtime.
