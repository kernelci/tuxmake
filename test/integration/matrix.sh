set -eu

tuxmake=${tuxmake:-tuxmake}

if [ -z "${ARCHITECTURE_LIST:-}" ]; then
  ARCHITECTURE_LIST="$(tuxmake --list-architectures)"
fi

if [ -z "${TOOLCHAIN_LIST:-}" ]; then
  TOOLCHAIN_LIST="$(tuxmake --list-toolchains)"
fi

rc=0
failed=
for arch in $ARCHITECTURE_LIST; do
  for toolchain in $TOOLCHAIN_LIST; do
    status=pass
    $tuxmake -a "${arch}" -t "${toolchain}" "$@" || status=fail
    if [ "${status}" = "fail" ]; then
      rc=1
    fi
    eval "status_${arch}_${toolchain}=${status}"
  done
done


# Header
printf "%10s" ""
for toolchain in $TOOLCHAIN_LIST; do
  printf "%-10s" "${toolchain}"
done
echo
# Data
for arch in $ARCHITECTURE_LIST; do
  printf "%-10s" "${arch}"
  for toolchain in $TOOLCHAIN_LIST; do
    eval "printf '%-10s' \"\$status_${arch}_${toolchain}\""
  done
  echo
done

exit "${rc}"
