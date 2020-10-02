if ! command -v tuxmake >/dev/null; then
  base=$(readlink -f $(dirname $0)/../..)
  export PYTHONPATH="${base}:${PYTHONPATH:+:}${PYTHONPATH:-}"
  export PATH="${base}/test/integration/bin:${PATH}"
fi
