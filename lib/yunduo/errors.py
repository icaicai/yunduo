
class DenyError(Exception):
    retry = True

    def __init__(self, *args, **kwargs):
        super(DenyError, self).__init__(*args, **kwargs)
        self.retry = kwargs.get('retry', True)


class ConfigError(Exception):
    pass


class DownloadError(Exception):
    pass


class ScriptError(Exception):
    pass


class FunctionNotFound(Exception):
    pass


class ScriptNotFound(Exception):
    pass
