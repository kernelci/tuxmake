#!/bin/sh

set -eu

tmpfile=$(mktemp)
trap 'rm -f $tmpfile' INT TERM EXIT

cp README.md "${tmpfile}"
sed -i -e 's#docs/##' "${tmpfile}"
cp "${tmpfile}" $@
