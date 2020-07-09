setUp() {
  tmpdir=$(mktemp --directory --tmpdir tuxmake-integration-tests-XXXXXXXXXX)
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

test_basic() {
  run tuxmake
  assertEquals 0 "$rc"
  assertTrue 'config: PASS' "grep 'config: PASS' stderr"
  assertTrue 'kernel: PASS' "grep 'kernel: PASS' stderr"
  assertFalse 'no ARCH=' 'grep ARCH= stdout'
  assertFalse 'no CROSS_COMPILE=' 'grep CROSS_COMPILE= stdout'
  assertFalse 'no CC=' 'grep CC= stdout'
}

test_cross() {
  run tuxmake --target-arch=arm64
  assertEquals 0 "$rc"
  assertTrue 'ARCH=' "grep 'ARCH=arm64' stdout"
  assertTrue 'CROSS_COMPILE=' "grep 'CROSS_COMPILE=aarch64-linux-gnu-' stdout"
  assertFalse 'no CC=' 'grep CC= stdout'
  assertTrue 'Image.gz' 'test -f $XDG_CACHE_HOME/tuxmake/builds/1/Image.gz'
}

test_toolchain() {
  run tuxmake --toolchain=gcc-10
  assertEquals 0 "$rc"
  assertFalse 'no ARCH=' 'grep ARCH= stdout'
  assertFalse 'no CROSS_COMPILE=' 'grep CROSS_COMPILE= stdout'
  assertTrue 'CC=' "grep 'CC=gcc-10' stdout"
}

test_cross_toolchain() {
  run tuxmake --target-arch=arm64 --toolchain=gcc-10
  assertEquals 0 "$rc"
  assertTrue 'ARCH=' "grep 'ARCH=arm64' stdout"
  assertTrue 'CROSS_COMPILE=' "grep 'CROSS_COMPILE=aarch64-linux-gnu-' stdout"
  assertTrue 'CC=' "grep 'CC=aarch64-linux-gnu-gcc-10' stdout"
  assertTrue 'Image.gz' 'test -f $XDG_CACHE_HOME/tuxmake/builds/1/Image.gz'
}

test_fail() {
  failrun kernel tuxmake
  assertEquals 2 "$rc"
  assertTrue 'grep "config: PASS" stderr'
  assertTrue 'grep "kernel: FAIL" stderr'
}

test_skip_kernel_if_config_fails() {
  failrun defconfig tuxmake
  assertTrue 'grep "config: FAIL" stderr'
  assertTrue 'grep "kernel: SKIP" stderr'
}

test_log_command_line() {
  run tuxmake --toolchain=gcc-10 --target-arch=arm64
  assertTrue 'command line logged' 'grep "tuxmake --toolchain=gcc-10 --target-arch=arm64" $XDG_CACHE_HOME/tuxmake/builds/1/build.log'
}

test_config_only() {
  run tuxmake --target-arch=arm64 config
  assertTrue "config produced" "test -f $XDG_CACHE_HOME/tuxmake/builds/1/config"
  assertFalse "kernel image not produced" "test -f $XDG_CACHE_HOME/tuxmake/builds/1/Image.gz"
}

test_modules() {
  run tuxmake modules
  assertTrue "build modules on defconfig" "grep 'modules: PASS' stderr"

  run tuxmake --kconfig=tinyconfig modules
  assertTrue "skip modules on tinyconfig" "grep 'modules: SKIP' stderr"
}

test_dtbs() {
  run tuxmake --target-arch=arm64 dtbs
  assertTrue "build dtbs on arm64" "grep 'dtbs: PASS' stderr"

  run tuxmake --target-arch=x86_64 dtbs
  assertTrue "does not build dtbs on x86_64" "grep 'dtbs: SKIP' stderr"
}


. shunit2
