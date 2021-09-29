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

# mutually exclusive options, used to simulate conflicting options and test
# tuxmake behavior in that case.
if grep -q '^CONFIG_XOR_1=y' "$dest" && grep -q '^CONFIG_XOR_2=y' "${dest}"; then
  echo "W: CONFIG_XOR_1 and CONFIG_XOR_2 are mutually exclusive; disabling CONFIG_XOR_2 in ${dest}"
  sed -i -e 's/^CONFIG_XOR_2=y/CONFIG_XOR_2=n/' "$dest"
fi

# turn CONFIG_SHOULD_NOT_BE_SET=n into `# CONFIG_SHOULD_NOT_BE_SET is not set`
sed -i -e 's/^\(CONFIG_SHOULD_NOT_BE_SET\)=n/# \1 is not set/' "$dest"
