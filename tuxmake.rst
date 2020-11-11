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

tuxmake [OPTIONS] [targets ...]

DESCRIPTION
===========

tuxmake helps you build Linux kernels in a repeatable and consistent way. It
supports multiple ways of configuring the kernel, multiple architectures,
toolchains, and can build multiple targets.

You can specify what **targets** to build using positional arguments.  If none
are provided, tuxmake will build a default set of targets: config, kernel,
modules and DTBs (if applicable). Other build options, such as target
architecture, toolchain to use, etc can be provided with command line options.

OPTIONS
=======
..
    Include the options from --help
.. include:: cli_options.rst


ENVIRONMENT VARIABLES
=====================

* `TUXMAKE`: defines default options for tuxmake. Those options can be
  overridden in the command line.
* `TUXMAKE_DOCKER_RUN`: defines extra options for `docker run` calls made
  by the docker runtime.
* `TUXMAKE_DOCKER_RUN`: defines extra options for `podman run` calls made
  by the podman runtime.
* `TUXMAKE_IMAGE`: defines the image to use with the selected container runtime
  (docker, podman etc).  The same substitutions described in `--image`
  apply.

..
    END OF ENVIRONMENT VARIABLES

SEE ALSO
========

The full tuxmake documentation: <https://docs.tuxmake.org/>
