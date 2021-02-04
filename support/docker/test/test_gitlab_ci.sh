set -u

setUp() {
    ci=$(mktemp)
}

tearDown() {
    rm -f "$ci"
}

test_gitlab_ci_is_update_to_date() {
  ./gen-gitlab-ci > "${ci}"
  diff -u gitlab-ci.yml ${ci}
  assertEquals "gitlab-ci.yml is up to date" 0 ${?}
}

. /usr/share/shunit2/shunit2
