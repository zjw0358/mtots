from mtots.util.dataclasses import dataclass
import typing
import re
from mtots import test


class Source(typing.NamedTuple):
    path: str
    data: str

    @staticmethod
    def from_string(data):
        return Source('<string>', data)


class Mark(typing.NamedTuple):
    source: Source
    start: int
    end: int
    main: typing.Optional[int] = None

    @property
    def i(self) -> int:
        return self.start if self.main is None else self.main

    @property
    def lineno(self) -> int:
        assert self.source is not None
        assert self.i is not None
        return self.source.data.count('\n', 0, self.i) + 1

    @property
    def colno(self) -> int:
        assert self.source is not None
        assert self.i is not None
        return self.i - self.source.data.rfind('\n', 0, self.i)

    @property
    def line(self) -> str:
        assert self.source is not None
        assert self.i is not None
        s = self.source.data
        a = s.rfind('\n', 0, self.i) + 1
        b = s.find('\n', self.i)
        if b == -1:
            b = len(s)
        return s[a:b]

    @property
    def info(self) -> str:
        line = self.line
        colno = self.colno
        lineno = self.lineno
        spaces = ' ' * (colno - 1)
        return f'on line {lineno}\n{line}\n{spaces}*\n'


class Token(typing.NamedTuple):
    mark: typing.Optional[Mark]
    type: str
    value: object

    def __repr__(self):
        return f'Token({repr(self.type)}, {repr(self.value)})'

    def __eq__(self, other):
        return (
            isinstance(other, Token) and
            self.type == other.type and
            self.value == other.value
        )


class Error(Exception):
    def __init__(self, marks, message):
        super().__init__(
            message + '\n' + ''.join(mark.info for mark in marks)
        )


@dataclass
class Node:
    mark: typing.Optional[Mark]


class Pattern(typing.NamedTuple):
    regex: typing.Pattern
    callback: typing.Callable[[typing.Match, Mark],
                              typing.Iterable[Token]]

    @staticmethod
    def new(regex: typing.Union[typing.Pattern, str]):
        regex = re.compile(regex)
        def wrapper(
                callback: typing.Callable[[typing.Match, Mark],
                                          typing.Iterable[Token]]):
            return Pattern(regex, callback)
        return wrapper


@dataclass
class TextStream:
    source: Source
    i: int

    def eof(self):
        return self.i >= len(self.source.data)


class Lexer:
    @staticmethod
    def new(f):
        lexer = Lexer()
        f(lexer)
        return lexer

    def __init__(self):
        self.patterns = []

    def add_pattern(self, pattern):
        self.patterns.append(pattern)
        return pattern

    def add(self, regex):
        def wrapper(callback):
            self.add_pattern(Pattern(
                re.compile(regex, re.MULTILINE | re.DOTALL),
                callback,
            ))
            return callback
        return wrapper

    def extract(self, stream):
        i = stream.i
        source = stream.source
        data = source.data

        for pattern in self.patterns:
            m = pattern.regex.match(data, i)
            if m:
                mark = Mark(source, m.start(), m.end())
                stream.i = m.end()
                return pattern.callback(m, mark)

        raise Error([Mark(source, i, i)], 'Unrecognized token')

    def lex(self, source):
        stream = TextStream(source, 0)
        while not stream.eof():
            yield from self.extract(stream)
        yield Token(Mark(source, stream.i, stream.i), 'EOF', None)

    def lex_string(self, s):
        return self.lex(Source.from_string(s))


@test.case
def test_sample_lexer():
    lexer = Lexer()

    @lexer.add('\s+')
    def spaces(m, mark):
        return ()

    @lexer.add('\w+')
    def name(m, mark):
        return [Token(mark, 'NAME', m.group())]

    test.equal(
        list(lexer.lex_string('a b cc')),
        [
            Token(None, 'NAME', 'a'),
            Token(None, 'NAME', 'b'),
            Token(None, 'NAME', 'cc'),
            Token(None, 'EOF', None),
        ]
    )

    @test.throws(Error, """Unrecognized token
on line 1
&
*
""")
    def lex_invalid_token():
        list(lexer.lex_string('&'))
