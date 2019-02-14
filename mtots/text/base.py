from mtots import test
from mtots.util.dataclasses import dataclass
import argparse
import json
import re
import sys
import typing


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

    def __repr__(self):
        return f'Mark({self.start}, {self.end}, {self.main})'


class Token(typing.NamedTuple):
    mark: typing.Optional[Mark]
    type: str
    explicit_value: object

    @property
    def value(self):
        if self.explicit_value is None:
            return self.type
        else:
            return self.explicit_value

    def __repr__(self):
        return f'Token({repr(self.type)}, {repr(self.explicit_value)})'

    def __eq__(self, other):
        return (
            isinstance(other, Token) and
            self.type == other.type and
            self.explicit_value == other.explicit_value
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

    class Builder:
        def __init__(self):
            self.patterns = []
            self.adapters = []

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

        def add_adapter(self, adapter):
            self.adapters.append(adapter)

        def build(self):
            return Lexer(patterns=self.patterns, adapters=self.adapters)

    @staticmethod
    def new(f):
        builder = Lexer.Builder()
        f(builder)
        return builder.build()

    def __init__(self, patterns, adapters):
        self._patterns = tuple(patterns)
        self._adapters = tuple(adapters)

    def _extract(self, stream):
        i = stream.i
        source = stream.source
        data = source.data

        for pattern in self._patterns:
            m = pattern.regex.match(data, i)
            if m:
                mark = Mark(source, m.start(), m.end())
                stream.i = m.end()
                return pattern.callback(m, mark)

        raise Error([Mark(source, i, i)], 'Unrecognized token')

    def _lex_without_adapters(self, source):
        stream = TextStream(source, 0)
        while not stream.eof():
            yield from self._extract(stream)
        yield Token(Mark(source, stream.i, stream.i), 'EOF', None)

    def lex(self, source):
        token_gen = self._lex_without_adapters(source)
        for adapter in self._adapters:
            token_gen = adapter(token_gen)
        return token_gen

    def lex_string(self, s):
        return self.lex(Source.from_string(s))

    def main(self):
        """Some functionality for if a lexer module
        is used as a main module.
        """
        parser = argparse.ArgumentParser()
        parser.add_argument('path', nargs='?')
        args = parser.parse_args()

        opened_file = bool(args.path)
        file = open(args.path) if args.path else sys.stdin
        try:
            path = args.path or '<stdin>'
            contents = file.read()
            source = Source(path, contents)
            for token in self.lex(source):
                print(json.dumps({
                    'type': token.type,
                    'value': token.value,
                    'mark': {
                        'start': token.mark.start,
                        'end': token.mark.end,
                        'main': token.mark.main,
                    },
                }))

        finally:
            if opened_file:
                file.close()


@test.case
def test_sample_lexer():
    builder = Lexer.Builder()

    @builder.add('\s+')
    def spaces(m, mark):
        return ()

    @builder.add('\w+')
    def name(m, mark):
        return [Token(mark, 'NAME', m.group())]

    lexer = builder.build()

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


@test.case
def test_lexer_with_adapter():

    @Lexer.new
    def lexer(builder):
        @builder.add('\s+')
        def spaces(m, mark):
            return ()

        @builder.add('\w+')
        def name(m, mark):
            return [Token(mark, 'NAME', m.group())]

        @builder.add_adapter
        def double_every_name_token(tokens):
            for token in tokens:
                if token.type == 'NAME':
                    yield token
                    yield token
                else:
                    yield token

    test.equal(
        list(lexer.lex_string('a b cc')),
        [
            Token(None, 'NAME', 'a'),
            Token(None, 'NAME', 'a'),
            Token(None, 'NAME', 'b'),
            Token(None, 'NAME', 'b'),
            Token(None, 'NAME', 'cc'),
            Token(None, 'NAME', 'cc'),
            Token(None, 'EOF', None),
        ]
    )

