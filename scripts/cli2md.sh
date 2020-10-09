#!/bin/sh

set -eu

tmpfile=$(mktemp)
trap 'rm -f $tmpfile' INT TERM EXIT
python3 $(dirname $0)/cli2md.py > "${tmpfile}"

sed -i -e '
1i # Command line reference\n
/^usage:/,/Positional arguments:/ {
	/^usage:/b continue
	/Positional arguments:/b continue
	d
}
:continue
s/^usage:/## Usage\n/
s/^\(\S.*\):$/## \1/
s/^  \(\S.*\)/### \1/
' "${tmpfile}"

sed -e '
/^ENVIRONMENT VARIABLES/,/^\.\./ !d
s/^[A-Z]/## &/
s/ENVIRONMENT VARIABLES/Environment variables/
/^==/d
/^\.\./d' tuxmake.rst >> "${tmpfile}"

cp "${tmpfile}" "$1"
