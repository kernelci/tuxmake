class TuxMakeException(Exception):
    def __str__(self):
        name = super().__str__()
        if hasattr(self, "msg"):
            return self.msg.format(name=name)
        else:
            return name


class UnsupportedTarget(TuxMakeException):
    msg = "Unsupported target: {name}"
    pass


class UnsupportedArchitecture(TuxMakeException):
    msg = "Unsupported architecture: {name}"
    pass


class UnsupportedToolchain(TuxMakeException):
    msg = "Unsupported toolchain: {name}"
    pass
