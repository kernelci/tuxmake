=======
tuxmake
=======

-----------------------------------------
A thin wrapper for building Linux kernels
-----------------------------------------

:Manual section: 1
:Author: Antonio Terceiro, 2020

SYNOPSIS
========

tuxmake [@config ...] [OPTIONS] [KEY=VALUE ...] [targets ...]

DESCRIPTION
===========

tuxmake helps you build Linux kernels in a repeatable and consistent way. It
supports multiple ways of configuring the kernel, multiple architectures,
toolchains, and can build multiple targets.

Any positional arguments in the command line that start with an `@` are used as
configuration file references. See **CONFIGURATION FILES** below.

Any **KEY=VALUE** pairs given in the command line are passed to make as is.
e.g. **LLVM=1**, **W=3**, etc.

You can specify what **targets** to build in the command line.  If none
are provided, tuxmake will build a default set of targets: config, kernel,
modules and DTBs (if applicable). Other build options, such as target
architecture, toolchain to use, etc can be provided with command line options.

OPTIONS
=======
..
    Include the options from --help
.. include:: cli_options.rst

.. BEGIN-EXPORT

CONFIGURATION FILES
===================

Configuration files can be passed as positional arguments that start with `@`.
Absolute filenames are read as is, and relative ones are assumed to be relative
to `${XDG_CONFIG_HOME}/tuxmake` (where `${XDG_CONFIG_HOME}` defaults to
`${HOME}/.config`).

The configuration files must contain command line options, for example::

    $ cat ~/.config/tuxmake/default
    --wrapper=ccache
    --runtime=podman

Whitespace is ignored in general, so your option can be one per line, or all in
one line.  Any option values containing spaces and other shell metacharacters
must be properly quoted and escaped, as if you were writing them in shell
script::

    --environment=KBUILD_BUILD_TIMESTAMP='Tue May 26 16:16:14 2020 -0500'

Lines starting with an `#` are comments and are ignored. No inline comments are
supported, only full lines.

When a configuration file reference is found in the command line, the file will
be read, and the command line options in it will be inserted in the command
line in the same position as the configuration file reference. So, any options
given before the configuration file reference can potentially be overridden by
the ones in the configuration file, and any options after the configuration
file reference can override the ones set in it.

If `${XDG_CONFIG_HOME}/tuxmake/default` exists, it is always loaded as if it
was the first argument in the command line.

**Note:** configuration files are only supported in the tuxmake command line.
The Python API always requires any options to be specified explicitly.

ENVIRONMENT VARIABLES
=====================

* `TUXMAKE`: defines default options for tuxmake. Those options can be
  overridden in the command line.
* `TUXMAKE_DOCKER_RUN`: defines extra options for `docker run` calls made
  by the docker runtime.
* `TUXMAKE_PODMAN_RUN`: defines extra options for `podman run` calls made
  by the podman runtime.
* `TUXMAKE_IMAGE`: defines the image to use with the selected container runtime
  (docker, podman etc).  The same substitutions described in `--image`
  apply.
* `TUXMAKE_IMAGE_REGISTRY`: defines an container image registry to get any
  container image from. This string, and a slash character ("/"), gets
  prepended to the image name, regardless of it being provided via
  `$TUXMAKE_IMAGE`, `--image`, or determined automatically by tuxmake.
* `TUXMAKE_IMAGE_TAG`: defines an container image tag to use.  If
  used, a colon character (":") and this string gets appended to the image name
  that was informed with `$TUXMAKE_IMAGE`, `--image`, or determined
  automatically by tuxmake.

FILES
=====

* `${XDG_CONFIG_HOME}/tuxmake/default` (`~/.config/tuxmake/default`): default
  configuration file.

.. END-EXPORT

SEE ALSO
========

The full tuxmake documentation: <https://tuxmake.org/>
