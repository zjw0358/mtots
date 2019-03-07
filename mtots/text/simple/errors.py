from mtots.text import base


LexError = base.LexError
ParseError = base.ParseError


class InvalidGrouping(LexError):
    pass


class InvalidEscape(LexError):
    pass

