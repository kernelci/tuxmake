def get_runner(build):
    return NullRunner()


class NullRunner:
    def get_command_line(self, cmd):
        return cmd
