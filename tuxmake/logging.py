import sys


def __log__(stream, prefix, *msgs):
    for m in msgs:
        print(f"{prefix}{m}", file=stream)


__quiet__ = False
__log_debug__ = False


def set_quiet(quiet):
    global __quiet__
    __quiet__ = quiet


def set_debug(debug):
    global __log_debug__
    __log_debug__ = debug


def error(*msgs):
    __log__(sys.stderr, "E: ", *msgs)


def warning(*msgs):
    __log__(sys.stderr, "W: ", *msgs)


def info(*msgs):
    if not __quiet__:
        __log__(sys.stderr, "I: ", *msgs)


def debug(*msgs):
    if __log_debug__:
        __log__(sys.stderr, "D: ", *msgs)
