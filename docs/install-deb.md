# Installing TuxMake via Debian packages

**Note:** TuxMake requires Python 3.6 or newer.

TuxMake provides Debian packages that have minimal dependencies, and should
work on any Debian or Debian-based (Ubuntu, etc) system.

1) Download the [repository signing key](https://tuxmake.org/packages/signing-key.gpg)
and save it to `/usr/share/keyrings/tuxmake.gpg`.

```
# wget -O /usr/share/keyrings/tuxmake.gpg \
  https://tuxmake.org/packages/signing-key.gpg
```

2) Create /etc/apt/sources.list.d/tuxmake.list with the following contents:

```
deb [signed-by=/usr/share/keyrings/tuxmake.gpg] https://tuxmake.org/packages/ ./
```

3) Install `tuxmake` as you would any other package:

```
# apt update
# apt install tuxmake
```

Upgrading tuxmake will work just like it would for any other package (`apt
update`, `apt upgrade`).
