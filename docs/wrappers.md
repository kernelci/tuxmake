# Compiler wrappers

Compiler wrappers can modify the behavior of compiler invocations, e.g. to
implement caching. The following wrappers are supported:

## none

No compilation wrapper (the default).

## ccache

Wraps compilers with [ccache](https://ccache.dev/). The cache directory can be
set via the regular `CCACHE_DIR` environment variable.

## sccache

Wraps compilers with [sccache](https://github.com/mozilla/sccache), a
cloud-enabled ccache-like compiler caching tool. The local cache directory can
eb set via the regular `SCCACHE_DIR` environment variable.
