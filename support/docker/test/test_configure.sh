set -u

oneTimeSetUp() {
    configure=$(mktemp)
    DEBUG=1 ./configure > "${configure}"
}

oneTimeTearDown() {
    rm -f "${configure}"
}

setUp() {
    stdout=$(mktemp)
}

tearDown() {
    rm -f "$stdout"
}

get_build_args() {
    sed -e "/^${1}:/,/^\$/!d" "${configure}" > "$stdout"
}

assertArg() {
    local failed=
    for arg in "$@"; do
        if ! grep -q "[-][-]build-arg=$arg" $stdout; then
            fail "\"$arg\" not found!"
            failed=1
        fi
    done
    if [ -n "$failed" ]; then
        echo ' /------------------------------------------------'
        sed -e 's/^/  | /' $stdout
        echo ' \------------------------------------------------'
    fi
}

test_base() {
    get_build_args base-debian
    assertArg 'BASE=debian:stable-slim'
}

test_gcc() {
    get_build_args gcc
    assertArg 'BASE=$(PROJECT)/base' 'PACKAGES="gcc g++"'
}

test_gcc_8() {
    get_build_args gcc-8
    assertArg 'BASE=$(PROJECT)/base' 'PACKAGES="gcc-8 g++-8"'
}

test_gcc_9() {
    get_build_args gcc-9
    assertArg 'BASE=$(PROJECT)/base-debian' 'PACKAGES="gcc-9 g++-9"'
}

test_arm64_gcc() {
    get_build_args arm64_gcc
    assertArg 'BASE=$(PROJECT)/gcc' 'HOSTARCH=aarch64'\
        'PACKAGES="gcc-aarch64-linux-gnu g++-aarch64-linux-gnu"'
}

test_arm64_gcc_8() {
    get_build_args arm64_gcc-8
    assertArg 'BASE=$(PROJECT)/gcc' 'HOSTARCH=aarch64'\
        'PACKAGES="gcc-8-aarch64-linux-gnu g++-8-aarch64-linux-gnu"'
}

test_clang() {
    get_build_args clang
    assertArg 'BASE=$(PROJECT)/base' 'PACKAGES="clang"'
}

test_clang8() {
    get_build_args clang-8
    assertArg 'BASE=$(PROJECT)/base' 'PACKAGES="clang-8"'
}

. shunit2
