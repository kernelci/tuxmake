#!/bin/sh

set -eu

# Accept the same arguments as the real script from Linux
# ########################################################################
# -h    display this help text
# -m    only merge the fragments, do not execute the make command
# -n    use allnoconfig instead of alldefconfig
# -r    list redundant entries when merging fragments
# -y    make builtin have precedence over modules
# -O    dir to put generated output files.  Consider setting $KCONFIG_CONFIG instead.
OPTS=`getopt --options=hmnryO: -- "$@"`
eval set -- "$OPTS"

# ignore options for now
while [ "$1" != "--" ]; do
  shift
done
shift # drop the --

dest="$1"
shift
for f in "$@"; do
  cat "$f" >> "$dest"
done
