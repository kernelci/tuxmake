# Contributing to tuxmake

## Source code

The tuxmake source code it available in the 
[tuxmake gitlab repository](https://gitlab.com/Linaro/tuxmake). To clone the
repository, run:

```console
git clone git@gitlab.com:Linaro/tuxmake.git
```

or if you don't (want to) have a gitlab account:

```console
git clone https://gitlab.com/Linaro/tuxmake.git
```

## Issue tracker

The tuxmake issue tracker is also on Gitlab:
<https://gitlab.com/Linaro/tuxmake/-/issues>.

## Development dependencies

The Python packages needed to develop tuxmake are listed in
`requirements-dev.txt`. You can either install them using
`pip install -r requirements-dev.txt`, or install the corresponding
distribution (e.g. Debian) packages. There are also a few non Python packages
used for development: `make`, `shunit2`, and `git`, `clang`, `git`.

Here is a single line that should get you everything that is needed on Debian
and derivatives:

```console
apt-get install bzip2 ccache clang codespell flake8 gcc git make mkdocs \
  mypy python3 python3-docutils python3-pip python3-pytest python3-pytest-cov \
  python3-pytest-mock shunit2
```

tuxmake has no runtime dependencies other than the Python core.

## Running the tests

To run the tests, just run `make`: it will run all the included tests,
including unit tests, integration tests, coding style checks, etc. Please make
sure all the tests pass before submitting patches.

## Sending your contributions.

Contributions should be sent as merge requests on the GitLab repository.

If that's too high of a barrier for you to send your patches, you can also send
them by email to the maintainers. However, we really prefer merge requests
because the GitLab Continuous Integration will run all the tests against your
changes, and that makes a lot easier for us to evaluate your contribution.
