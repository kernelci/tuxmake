setUp() {
  tmpdir=$(mktemp -d)
  export XDG_CACHE_HOME="${tmpdir}/cache"
  cp -r test/fakelinux/ "${tmpdir}/linux"
  cd "${tmpdir}/linux"
}

tearDown() {
  cd - >/dev/null
  rm -rf "${tmpdir}"
}

failrun() {
  export FAIL="$1"
  shift
  run "$@"
  unset FAIL
}

run() {
  rc=0
  "$@" > stdout 2> stderr || rc=$?
  cat stdout stderr | sed -e 's/^/    /'
  export rc
}

test_pass() {
  run tuxmake
  assertEquals 0 "$rc"
  assertTrue "grep 'config: PASS' stderr"
  assertTrue "grep 'config: PASS' stderr"
}

test_fail() {
  failrun kernel tuxmake
  assertEquals 2 "$rc"
  assertTrue 'grep "config: PASS" stderr'
  assertTrue 'grep "kernel: FAIL" stderr'
}

. shunit2
