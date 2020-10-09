set -u
export testdir=$(readlink -f $(dirname $0)/..)

if ! command -v tuxmake >/dev/null; then
  base=$(readlink -f $(dirname $0)/../..)
  export PYTHONPATH="${base}:${PYTHONPATH:+:}${PYTHONPATH:-}"
  export PATH="${base}/test/integration/bin:${PATH}"
fi

oneTimeSetUp() {
  rootdir=${TMPDIR:-/tmp}/tuxmake-integration-tests-${USER:-user}
  local i
  if [ -d "${rootdir}" ]; then
    i=$(cd "${rootdir}" && ls -1d [0-9]* | sort -V | tail -1)
    i=$((i+1))
  else
    mkdir "${rootdir}"
    i=1
  fi
  while true; do
    basetmpdir=${rootdir}/${i}
    if mkdir --mode=0700 "${basetmpdir}" 2>/dev/null; then
      ln -sfT ${i} ${rootdir}/latest
      break
    fi
    i=$((i+1))
  done
}

oneTimeTearDown() {
  # delete old tmpdirs
  (cd "$rootdir" && ls -1d [0-9]* | sort -rV | sed -e '1,5d' | xargs --no-run-if-empty rm -rf)
}

setUp() {
  tmpdir=$(mktemp --directory --tmpdir="${basetmpdir}")
  export XDG_CACHE_HOME="${tmpdir}/cache"
  cp -r $testdir/fakelinux/ "${tmpdir}/linux"
  cd "${tmpdir}/linux"
}

tearDown() {
  cd - >/dev/null
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
