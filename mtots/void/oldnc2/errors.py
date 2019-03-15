from mtots.parser import base


class Error(base.Error):
    pass


class LexError(Error):
    pass


class TypeError(Error):
    pass


class MissingReference(TypeError):
    pass

