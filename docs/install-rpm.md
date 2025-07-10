# Installing TuxMake via RPM packages

**Note:** TuxMake requires Python 3.6 or newer.

TuxMake provides RPM packages that have minimal dependencies, and should work
on any RPM-based (Fedora, etc) system. The instructions below were tested on
Fedora 33, you may need to adapt them to your system.

1) Create `/etc/yum.repos.d/tuxmake.repo` with the following contents:

```
[tuxmake]
name=tuxmake
type=rpm-md
baseurl=https://tuxmake.org/packages/
gpgcheck=1
gpgkey=https://tuxmake.org/packages/repodata/repomd.xml.key
enabled=1

```

2) Install tuxmake as you would any other package:

```
# dnf install tuxmake
```

Upgrades will be available in the same repository, so you can get them using
the same procedure you already use to get other updates for your system.

## Troubleshooting

If trying to do a build fails with the following error:

```
Writing manifest to image destination
a75ea7279dcf278b65f20bd8c7fe97c48c994463c1818fa388da938c681a315d
Error: lsetxattr /usr/share/tuxmake/tuxmake/runtime/bin: operation not permitted
E: Runtime preparation failed: failed to pull remote image docker.io/tuxmake/arm64_clang-20
```

Then, add the following rule to SELinux:

```
sudo chcon -Rt container_file_t /usr/share/tuxmake
```
