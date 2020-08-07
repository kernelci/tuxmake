ARG BASE
FROM ${BASE}

ENV DEBIAN_FRONTEND=noninteractive

ARG DOWNLOAD_SITE=https://github.com/foss-for-synopsys-dwc-arc-processors/toolchain/releases/download

# Change these when upgrading to a new release
ARG RELEASE=arc-2020.03-release
ARG TARBALL=arc_gnu_2020.03_prebuilt_elf32_le_linux_install.tar.gz
ARG GCC_VERSION=9
ARG GCC_VERSION_FULL=9.3.1
COPY arc.sha256sum /

RUN apt-get install \
        --assume-yes \
        --no-install-recommends \
        --option=debug::pkgProblemResolver=yes \
        gcc \
    && wget --progress=dot:giga $DOWNLOAD_SITE/$RELEASE/$TARBALL \
    && sha256sum -c arc.sha256sum \
    && tar -C /usr/local --strip-components=1 -xaf $TARBALL \
    && ln -sf arc-elf32-gcc-$GCC_VERSION_FULL /usr/local/bin/arc-elf32-gcc-$GCC_VERSION \
    && rm -f $TARBALL arc.sha256sum

# vim: ft=dockerfile
