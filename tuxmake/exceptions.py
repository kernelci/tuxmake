class TuxMakeException(Exception):
    def __str__(self):
        name = super().__str__()
        if hasattr(self, "msg"):
            return self.msg.format(name=name)
        else:
            return name


class TuxMakeInfrastructureError(TuxMakeException):
    """
    Subclasss of this exception type are raised when tuxmake can't recover from
    a situation caused by an error in tuxmake itself, or a failure in
    infrastructure that tuxmake is using to perform a build.
    """

    pass


class TuxMakeUserError(TuxMakeException):
    """
    Subclasss of this exception type are raised when tuxmake can't recover from
    invalid user input, or invalid build options.
    """

    pass


class UnrecognizedSourceTree(TuxMakeUserError):
    msg = "{name} does not look like a Linux source tree"


class UnsupportedTarget(TuxMakeUserError):
    msg = "Unsupported target: {name}"
    pass


class UnsupportedArchitecture(TuxMakeUserError):
    msg = "Unsupported architecture: {name}"
    pass


class UnsupportedToolchain(TuxMakeUserError):
    msg = "Unsupported toolchain: {name}"
    pass


class UnsupportedWrapper(TuxMakeUserError):
    msg = "Unsupported compiler wrapper: {name}"
    pass


class UnsupportedKconfig(TuxMakeUserError):
    msg = "Unsupported kconfig: {name}"


class InvalidKConfig(TuxMakeUserError):
    msg = "Invalid kconfig: {name}"


class UnsupportedKconfigFragment(TuxMakeUserError):
    msg = "Unsupported kconfig fragment: {name}"


class InvalidRuntimeError(TuxMakeUserError):
    msg = "Invalid runtime: {name}"


class UnsupportedArchitectureToolchainCombination(TuxMakeUserError):
    msg = "Unsupported architecture/toolchain combination: {name}"


class UnsupportedMakeVariable(TuxMakeUserError):
    msg = "Can't set make variable {name}= as it would break normal tuxmake operation"


class RuntimePreparationFailed(TuxMakeInfrastructureError):
    msg = "Runtime preparation failed: {name}"


class UnsupportedMetadata(TuxMakeInfrastructureError):
    msg = "Unsupported metadata extractor: {name}"
    pass


class UnsupportedMetadataType(TuxMakeInfrastructureError):
    msg = "Unsupported metadata type: {name}"
    pass
