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
are privided, tuxmake will build a default set of targets: config, kernel,
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
  overriden in the command line.
* `TUXMAKE_DOCKER_RUN`: defines extra options for the `docker run` calls made
  by the docker runtime.
* `TUXMAKE_DOCKER_IMAGE`: defines docker image to use with the docker runtime.
  The same substitutions described in `--docker-image` apply.

..
    END OF ENVIRONMENT VARIABLES

SEE ALSO
========

The full tuxmake documentation: <https://docs.tuxmake.org/>
