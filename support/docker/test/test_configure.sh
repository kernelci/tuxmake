set -u

oneTimeSetUp() {
    configure=$(mktemp)
    printf "checkconfig:\n\t@true\n\n" > "${configure}"
    DEBUG=1 ./configure >> "${configure}"
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

test_gcc() {
    get_build_args gcc
    assertArg 'BASE=$(REGISTRY)$(PROJECT)/base' 'PACKAGES="gcc g++"'
}

test_gcc_9() {
    get_build_args gcc-9
    assertArg 'BASE=$(REGISTRY)$(PROJECT)/base-debian' 'PACKAGES="gcc-9 g++-9"'
}

test_arm64_gcc() {
    get_build_args arm64_gcc
    assertArg 'BASE=$(REGISTRY)$(PROJECT)/gcc' 'HOSTARCH=aarch64'\
        'PACKAGES="gcc g++ gcc-arm-linux-gnueabihf g++-arm-linux-gnueabihf gcc-aarch64-linux-gnu g++-aarch64-linux-gnu"'
}

test_x86_64_gcc() {
    get_build_args x86_64_gcc
    assertArg 'BASE=$(REGISTRY)$(PROJECT)/gcc' 'HOSTARCH=x86_64'\
        'PACKAGES="gcc g++"'
}

test_clang() {
    get_build_args clang
    assertArg 'BASE=$(REGISTRY)$(PROJECT)/base' 'PACKAGES="clang clang-tidy llvm lld"'
}

test_arm64_clang() {
    get_build_args arm64_clang
    assertArg 'BASE=$(REGISTRY)$(PROJECT)/clang' 'HOSTARCH=aarch64' \
        'PACKAGES="clang clang-tidy llvm lld binutils-arm-linux-gnueabihf binutils-aarch64-linux-gnu"'
}

test_clang_11() {
    get_build_args clang-11
    assertArg 'BASE=$(REGISTRY)$(PROJECT)/base' 'PACKAGES="clang-11 clang-tidy-11 llvm-11 lld-11"'
}

test_gcc_all_includes_only_gcc_images_not_gcc_N() {
    make -f "${configure}" list > "${stdout}"
    if grep -q '^gcc_all.*gcc-[0-9]' "${stdout}"; then
        fail "gcc_all should not include gcc-N"
        echo ' /------------------------------------------------'
        grep ^gcc_all "${stdout}" | sed -e 's/^/ | /' | grep --color 'gcc-[0-9]\+'
        echo ' \------------------------------------------------'
    fi
}

test_clang_all_includes_only_glang_images_not_clang_N() {
    make -f "${configure}" list > "${stdout}"
    if grep -q '^clang_all.*clang-[0-9]' "${stdout}"; then
        fail "clang_all should not include clang-N"
        echo ' /------------------------------------------------'
        grep ^clang_all "${stdout}" | sed -e 's/^/ | /' | grep --color 'clang-[0-9]\+'
        echo ' \------------------------------------------------'
    fi
}

if [ "$(uname -m)" != "x86_64" ]; then
    echo "I: skipping tests, as they only apply on x86_64"
    exit
fi

. /usr/share/shunit2/shunit2
