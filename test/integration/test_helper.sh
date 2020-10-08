set -u
export testdir=$(readlink -f $(dirname $0)/..)

if ! command -v tuxmake >/dev/null; then
  base=$(readlink -f $(dirname $0)/../..)
  export PYTHONPATH="${base}:${PYTHONPATH:+:}${PYTHONPATH:-}"
  export PATH="${base}/test/integration/bin:${PATH}"
fi

setUp() {
  tmpdir=$(mktemp --directory --tmpdir tuxmake-integration-tests-XXXXXXXXXX)
  export XDG_CACHE_HOME="${tmpdir}/cache"
  cp -r $testdir/fakelinux/ "${tmpdir}/linux"
  cd "${tmpdir}/linux"
}

tearDown() {
  cd - >/dev/null
  rm -rf "${tmpdir}"
}

run() {
  if [ "${TMV:-}" = 1 ]; then
    echo '    $' "$@"
  fi
  rc=0
  "$@" > stdout 2> stderr || rc=$?
  if [ "${TMV:-}" = 1 ]; then
    cat stdout stderr | sed -e 's/^/    /'
  fi
  export rc
}
