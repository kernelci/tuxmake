# Toolchains

Toolchains can be specified only by their name, or with a version number
attached. For example, `clang` will use whatever `clang` binary you have in
your `$PATH`, while `clang-10` will specifically use `clang` version 10.

## gcc

This toolchain will use `gcc` as compiler. It is the default if you don't
request a specific toolchain. Specify `gcc-N` for requesting specific `gcc`
versions.

## clang

This toolchain uses `clang` as compiler, but the GNU binutils tools for
assembling and linking. Specify `clang-N` for specific versions. Special
variants of `clang` are also available:

| Variant | Description |
|---------|-------------|
| `clang-nightly` | Nightly clang builds, updated daily |
| `clang-android` | The exact clang compiler used for official Android builds |

## llvm

This toolchain does a full LLVM build, i.e. one with `LLVM=1`: compile with
clang, and assemble/link with the LLVM tools. Specify `llvm-N` for requesting
specific LLVM versions. As with `clang`, the `llvm-nightly` and `llvm-android`
are also available.

## rustgcc

This toolchain uses `gcc` as C compiler, and also includes the tools required
to build the kernel with [Rust support](https://github.com/Rust-for-Linux).

Alias: `rust`

## rustclang

This toolchain uses `clang` as C compiler, and also includes the tools required
to build the kernel with [Rust support](https://github.com/Rust-for-Linux).

## rustllvm

This toolchain does a full LLVM build for C code (i.e. `LLVM=1`), and also
includes the tools required to build the kernel with
[Rust support](https://github.com/Rust-for-Linux).
