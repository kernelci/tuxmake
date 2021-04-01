# Running TuxMake uninstalled

**Notes:**

- TuxMake requires Python 3.6 or newer.
- The offline builds feature requires `socat`, consider installing it.

If you don't want to or can't install TuxMake, you can run it directly from the
source directory. After getting the sources via git or something else, there is
a `run` script that will do the right think for you: you can either use that
script directly, or symlink it to a directory in your `PATH`.

```
/path/to/tuxmake/run --help
sudo ln -s /path/to/tuxmake/run /usr/local/bin/tuxmake && tuxmake --help
```
