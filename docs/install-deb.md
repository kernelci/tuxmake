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
sudo apt update
sudo apt install tuxmake
```

Upgrading tuxmake will work just like it would for any other package (`apt
update`, `apt upgrade`).

## Install using Debian extrepo

extrepo is a tool that helps configuring external repositories on
Debian in a secure manner. As a pre-requisite for installation using
this method, extrepo should be installed in your Debian machine.

1) Install extrepo if it is not installed previously:

```
sudo apt update
sudo apt install extrepo
```

2) Enable the tuxmake repository with extrepo:

```
sudo extrepo enable tuxmake
```

3) Install tuxmake as you would any other package:

```
sudo apt update
sudo apt install tuxmake
```

If the URL or the GPG key has changed, once updated in the
extrepo-data repository, it can be easily updated with:

```
sudo extrepo update tuxmake
```
