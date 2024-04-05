The TuxMake runtime library supports running commands in a way that makes
whether those commands are running on the host system or, say, inside a
container, transparent to the caller. It's what TuxMake itself uses to drive
its builds, but starting at TuxMake 1.0, it is completely independent of the
TuxMake build machinery and can be used for other purposes.

Using the runtime machinery looks like this:

```python
from tuxmake.runtime import Runtime

runtime = Runtime.get(os.environ.get("RUNTIME", "podman")
runtime.set_image(os.environ.get("IMAGE", "debian"))
runtime.prepare()
runtime.run_cmd(["date"])
runtime.cleanup()
```

## The `Runtime` class

::: tuxmake.runtime.Runtime
    :docstring:
    :members: get set_image set_user set_group add_volume prepare run_cmd cleanup log get_metadata

## The `Terminated` class

::: tuxmake.runtime.Terminated
    :docstring:
