from mtots import test
from mtots.util import dataclasses
from mtots.util.dataclasses import dataclass
from mtots.util.typing import Iterator
from mtots.util.typing import Tuple
import argparse
import json
import re
import sys
from mtots.util import typing


@dataclass(frozen=True)
class Source:
    path: str
    data: str
    metadata: object = None

    @staticmethod
    def from_string(data):
        return Source('<string>', data)


@dataclass(frozen=True)
class Mark:
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
        return f'{self.source.path} line {lineno}\n{line}\n{spaces}*\n'

    def __repr__(self):
        return f'Mark({self.start}, {self.end}, {self.main})'

    def join(self, middle: typing.Optional['Mark'], end: 'Mark'):
        if middle is None:
            middle = self
        return Mark(
            source=self.source,
            start=self.start,
            main=middle.main,
            end=end.end,
        )


@dataclass(frozen=True)
class Token:
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


@dataclass(frozen=True)
class Node:
    mark: typing.Optional[Mark] = dataclasses.field(
        compare=False,
        repr=False,
    )

    @staticmethod
    def dict(node):
        args = {'mark': node.mark}
        for field_name in type(node).__dataclass_fields__:
            args[field_name] = getattr(node, field_name)
        return args


@dataclass(frozen=True)
class Pattern:
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


class TokenStream:
    def __init__(self, tokens: Iterator[Token]):
        self.tokens = list(tokens)
        self.i = 0

        # cache to be used only by combinator.Forward
        # for memoizing results.
        self._cache = {}

    def __iter__(self):
        return self

    def __next__(self):
        if self.i < len(self.tokens):
            token = self.peek
            self.i += 1
            return token
        else:
            raise StopIteration

    @property
    def peek(self):
        return self.tokens[self.i]

    @property
    def state(self):
        return self.i

    @state.setter
    def state(self, value):
        self.i = value


@dataclass
class MatchResult:
    mark: Mark = dataclasses.field(compare=False, repr=False)

    @property
    def source(self):
        return self.mark.source


@dataclass
class Success(MatchResult):
    value: object


@dataclass
class Failure(MatchResult):
    message: str

    def __bool__(self):
        return False

    def to_error(self):
        return Error([self.mark], self.message)


class Parser:
    """Helper base class for anyone implementing their own hand-written
    recursive descent parser.
    """

    class Builder:
        def __init__(self):
            self.rule_map = {}

        def add_rule(self, f):
            self.rule_map[f.__name__] = f
            return f

        def build(self):
            return Parser(rule_map=self.rule_map)

    class Context:
        def __init__(self, parser, stream):
            self.parser = parser
            self.stream = stream

        @property
        def state(self):
            return self.stream.state

        @state.setter
        def state(self, new_state):
            self.stream.state = new_state

        @property
        def peek(self):
            return self.stream.peek

        @property
        def mark(self):
            return self.peek.mark

        def gettok(self):
            return next(self.stream)

        def at(self, token_type):
            return self.peek.type == token_type

        def consume(self, token_type):
            if self.peek.type == token_type:
                return self.gettok()

        def expect(self, token_type):
            token = self.consume(token_type)
            if token:
                return token
            else:
                raise Error(
                    [self.mark],
                    f'Expected {token_type} but got {self.peek.type}',
                )

    @staticmethod
    def new(f):
        builder = Parser.Builder()
        f(builder)
        return builder.build()

    def __init__(self, *, rule_map):
        self.rule_map = rule_map

    def parse(
            self,
            rule_name,
            tokens,
            *,
            rule_args=(),
            rule_kwargs=None,
            all=True):
        if rule_kwargs is None:
            rule_kwargs = {}
        stream = TokenStream(tokens)
        ctx = Parser.Context(parser=self, stream=stream)
        result = self.rule_map[rule_name](ctx, *rule_args, **rule_kwargs)
        if all and not ctx.at('EOF'):
            raise Error(
                [ctx.mark],
                f'Expected EOF but got {ctx.peek.type}',
            )
        return result


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
<string> line 1
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


@test.case
def test_sample_parser():

    @Lexer.new
    def lexer(builder):
        @builder.add('\s+')
        def spaces(m, mark):
            return ()

        @builder.add('\d+')
        def name(m, mark):
            return [Token(mark, 'INT', int(m.group()))]

        @builder.add('\(|\)|\+|\-|\*|\/|\%')
        def add_symbol(m, mark):
            return [Token(mark, m.group(), None)]

    @Parser.new
    def parser(builder):
        @builder.add_rule
        def expr(ctx):
            return add_expr(ctx)

        def atom_expr(ctx):
            int_token = ctx.consume('INT')
            if int_token:
                return int_token.value

            if ctx.consume('('):
                result = expr(ctx)
                ctx.expect(')')
                return result

            raise Error([mark], 'Expected expression')

        def mul_expr(ctx):
            lhs = atom_expr(ctx)
            while True:
                if ctx.consume('*'):
                    lhs *= atom_expr(ctx)
                elif ctx.consume('/'):
                    lhs /= atom_expr(ctx)
                elif ctx.consume('%'):
                    lhs %= atom_expr(ctx)
                else:
                    break
            return lhs

        def add_expr(ctx):
            lhs = mul_expr(ctx)
            while True:
                if ctx.consume('+'):
                    lhs += mul_expr(ctx)
                elif ctx.consume('-'):
                    lhs -= mul_expr(ctx)
                else:
                    break
            return lhs

    def parse(s):
        return parser.parse('expr', lexer.lex_string(s))

    test.equal(parse("12 + 3"), 15)
    test.equal(parse("12 + 3 * 5"), 27)
    test.equal(parse("(12 + 3) * 5"), (12 + 3) * 5)
    test.equal(parse("(12 - 3) * 5"), (12 - 3) * 5)
    test.equal(parse("12 + 3 / 5"), 12 + 3 / 5)
    test.equal(parse("(12 + 3) / 5"), (12 + 3) / 5)

