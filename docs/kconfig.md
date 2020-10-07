# Kernel Configuration

Both the [command line](cli.md) and the [Python API](python.md) have two
arguments for configuration: `--kconfig`/`kconfig` and
`--kconfig-add`/`kconfig_add`.

**kconfig** can only be specified once, and specifies the *main kernel
configuration*. It can be specified in three different ways:

- a named configuration target (`defconfig`, etc);
- a path to a config file on the local filesystem;
- a URL to a config file, in which case TuxMake will download it.

**kconfig_add** specifies extra configuration to apply on top of the main
configuration specified by *kconfig*. It can be specified in the following
ways:

- an in-tree configuration target (e.g. `kvm_guest.config`);
- a path to a config file on the local filesystem;
- a URL to a config file, in which case TuxMake will download it;
- a config fragment matching one of these:
    - `CONFIG_*=[y|m|n]`
    - `# CONFIG_* is not set`

`kconfig_add` can be specified multiple times. Any in-tree configuration target
will be built with `make`, and then all of the others will be saved to a local
file in the order they were passed. They will be then merged on top of the
existing configuration by calling `scripts/kconfig/merge_config.sh` and
`make olddefconfig`.
