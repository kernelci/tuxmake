#!/bin/bash

set -eu;


setUp() {
  apk add py3-pip git podman
  # Install tuxmake and tuxrun
  pip3 install --force-reinstall tuxmake tuxrun;
  apk add --no-cache --update  fuse-overlayfs linux-virt
  tuxmake --version;
  tuxrun --version;
  # Clone linux kernel source
  git clone --depth=1 --branch=master https://github.com/torvalds/linux.git;
}

cleanUp() {
  # Remove the build directory if it exists
  if [ -d "build" ]; then
  rm -rf build;
  echo "Build directory removed."
  fi
}


# Check container image tag
if [ -z "${1:-}" ]; then
  echo "Missing container tag. Exiting."
  exit 1
fi

IMAGE_TAG=$1;

# Check if the linux directory already exists
if [ -d "linux" ]; then
  echo "Linux directory already exists. Skipping clone."
else
  setUp
fi

# Perform build
tuxmake -C linux/ -o build/ -r docker-local -i $IMAGE_TAG;

# Perform boot test
tuxrun --tuxmake build/;

# Clean build directory
cleanUp