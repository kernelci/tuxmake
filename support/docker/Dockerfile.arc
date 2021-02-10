ARG BASE
FROM ${BASE}

ENV DEBIAN_FRONTEND=noninteractive

ARG DOWNLOAD_SITE=https://github.com/foss-for-synopsys-dwc-arc-processors/toolchain/releases

# Change these when upgrading to a new release
ARG RELEASE
ARG TARBALL
ARG GCC_VERSION
ARG GCC_VERSION_FULL
COPY arc-gcc-$GCC_VERSION.sha256sum /

RUN apt-get update && \
    apt-get install \
        --assume-yes \
        --no-install-recommends \
        --option=debug::pkgProblemResolver=yes \
        gcc \
    && wget --progress=dot:giga $DOWNLOAD_SITE/download/$RELEASE/$TARBALL \
    && sha256sum -c arc-gcc-$GCC_VERSION.sha256sum \
    && tar -C /usr/local --strip-components=1 --no-same-owner -xaf $TARBALL \
    && ln -sf arc-elf32-gcc-$GCC_VERSION_FULL /usr/local/bin/arc-elf32-gcc-$GCC_VERSION \
    && rm -f $TARBALL arc.sha256sum

# vim: ft=dockerfile
