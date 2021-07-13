# Metadata

At the end of each build, one of the artifacts left in the output directory
will be a metadata file, called `metadata.json`. The metadata file will contain
a JSON object, with exactly 2 levels of depth. The first level will have
metadata "group" names as keys, and their data as values. Those values (the
second level) will contain key/value pairs with the actual metadata items.

Any items or entire groups can be omitted if they don't apply to the build in
question. For example, if your build didn't use `ccache`, then there will be no
`ccache` metadata available. **build** and **results** metadata are always
available.


- **artifacts**: metadata about the artifacts.
    - **modules**: list of modules built with the kernel and included in `modules.tar.xz` (list of strings).
    - **dtbs**: list of dtbs built with the kernel and included in `dtbs.tar.xz` (list of strings).
- **build**: metadata about the build options.
    - **targets**: list of targets names built (list of strings).
    - **target_arch**: name of the target architecture (string).
    - **toolchain**: name of the toolchain used (string).
    - **wrapper**: compiler wrapper used (string).
    - **environment**: environment variables passed to the build (key/value - all strings).
    - **kconfig**: name of the kernel config (string).
    - **kconfig_add**: extra kernel config file or fragments (list of strings).
    - **jobs**: number of concurrent jobs (integer).
    - **reproducer_cmdline**: command line that can be used to reproduce the build with tuxmake (list of strings).
    - **runtime**: name of the runtime used for the build (string).
    - **verbose**: whether this was a verbose build (boolean).
- **ccache**: ccache statistics. Requires `ccache` 3.7 and later versions.
    - **cache_hits**: number of cache hits (integer).
    - **cache_misses**: number of cache misses (integer).
- **compiler**: information about the compiler used in the build.
    - **name**: name of the compiler (string).
    - **version**: short compiler version (string).
    - **version_full**: full compiler version (string).
- **git**: metadata about the source git repository.
    - **git_describe**: output of `git describe --tags`.
    - **git_branch**: the git branch.
    - **git_commit**: the git commit hash at HEAD.
    - **git_url**: the URL of the `origin` remote.
- **hardware**: metadata about the build hardware
    - **cores**: number or cores, as reported by `nproc`.
    - **ram**: amount of RAM, in megabytes.
    - **free_disk_space**: amount of disk space available in the build
      directory, before the build starts, in megabytes.
- **os**: metadata about the OS used in the build. When using a container
  runtime, this will refer to the OS in the container, and not in the host
  system.
    - **name**: OS name.
    - **version**: OS version.
- **resources:** resources used by the build
    - **disk_usage:** amount of disk space used in the kernel build directory,
      in megabytes (does not include the disk space taken by the source directory).
- **results**: metadata about the build results
    - **status**: "PASS" or "FAIL" (string).
    - **targets**: key/value with target names as keys. Values are objects with
      the following fields:
        * **status**: target status: "PASS", "FAIL", or "SKIP" (string).
        * **duration**: duration of this target build, in seconds (number).
    - **artifacts**: key/value with target names (string) as keys, and list of
      artifacts built for that target (list of strings).
    - **errors**: number of errors in the build (integer).
    - **warnings**: number of warnings in the build (integer).
- **sccache**: sccache statistics.
    - **cache_hits**: number of cache hits (integer).
    - **cache_misses**: number of cache misses (integer).
- **source**: metadata about the source tree.
    - **kernelrelease**: output of `make --silent kernelrelease`
    - **kernelversion**: output of `make --silent kernelversion`
- **system_map**: metadata about `System.map`.
    - **text_offset**: offset of the .text section in hexadecimal (string).
- **tools**: metadata about tools present in the build system. key/value, with
  the tool name (e.g. "gcc", "make", "ld", etc), and their version
- **uname**: different components of *uname(1)*.
    - **kernel**: output of `uname --kernel-name`.
    - **kernel_release**: output of `uname --kernel-release`.
    - **kernel_version**: output of `uname --kernel-version`.
    - **machine**: output of `uname --machine`.
    - **operating_system**: output of `uname --operating-system`.
- **vmlinux**: information about the `vmlinux` kernel binary.
    - **bss_size**: size in bytes of the `.bss` section in the ELF file.
    - **data_size**: size in bytes of the `.data` section in the ELF file.
    - **text_size**: size in bytes of the `.text` section in the ELF file.
    - **file_size**: total file size in bytes
