"""Parser combinator
"""
from . import base
from mtots import test
from mtots.util.dataclasses import dataclass
import abc
import functools
import math
import typing


_INF = 1 << 62  # Effectively infinite integer


class TokenStream:
    def __init__(self, tokens: typing.Iterator[base.Token]):
        self.tokens = list(tokens)
        self.i = 0

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
    mark: base.Mark


@dataclass
class Success(MatchResult):
    value: object

    def __str__(self):
        return f'Success({self.value})'

    def __eq__(self, other):
        return type(self) is type(other) and self.value == other.value


@dataclass
class Failure(MatchResult):
    message: str

    def __bool__(self):
        return False

    def __str__(self):
        return f'Failure({repr(self.message)})'

    def __eq__(self, other):
        return type(self) is type(other) and self.message == other.message


class Pattern(abc.ABC):

    @staticmethod
    def ensure_pattern(s):
        if isinstance(s, Pattern):
            return s
        elif isinstance(s, str):
            return Token(s)
        else:
            assert False, f'{repr(s)} is not a pattern'

    def parse(self, tokens: typing.Iterable[base.Token]) -> MatchResult:
        return self.match(TokenStream(tokens))

    @abc.abstractmethod
    def match(self, stream: TokenStream) -> MatchResult:
        pass

    def allmap(self, f):
        """Creates a new pattern that mutates the MatchResult with the
        given callback
        """
        return AllMap(self, f)

    def xmap(self, f):
        """'Cross' map
        Like allmap, but only triggers when MatchResult succeeds
        """

        @functools.wraps(f)
        def g(match_result):
            if match_result:
                return f(match_result)
            else:
                return match_result

        return self.allmap(g)

    def recover(self, f):
        """Like allmap, but only triggers when MatchResult fails
        """

        @functools.wraps(f)
        def g(match_result):
            if match_result:
                return match_result
            else:
                return f(match_result)

        return self.allmap(g)

    def map(self, f):

        @functools.wraps(f)
        def g(match_result):
            return Success(match_result.mark, f(match_result.value))

        return self.xmap(g)

    def repeat(self, min=0, max=_INF):
        return Repeat(self, min, max)

    def __or__(self, other):
        return Any(self, other)


@dataclass
class Token(Pattern):
    type: str

    def match(self, stream):
        mark = stream.peek.mark
        if stream.peek.type == self.type:
            return Success(mark, next(stream).value)
        else:
            return Failure(
                mark,
                f'Expected {self.type} but got {stream.peek.type}',
            )

    def __str__(self):
        return repr(self.type)


class CompoundPattern(Pattern):
    def __str__(self):
        return f'{type(self).__name__}({", ".join(map(str, self.patterns))})'


class Any(CompoundPattern):
    def __init__(self, *patterns):
        _patterns = []
        for pattern in patterns:
            if isinstance(pattern, Any):
                _patterns.extend(pattern.patterns)
            else:
                _patterns.append(Pattern.ensure_pattern(pattern))
        self.patterns = tuple(_patterns)

    def match(self, stream):
        mark = stream.peek.mark
        result = Failure(mark, 'Zero pattern Any')
        for pattern in self.patterns:
            result = pattern.match(stream)
            if result:
                return result
        return result


class All(CompoundPattern):
    def __init__(self, *patterns):
        self.patterns = tuple(map(Pattern.ensure_pattern, patterns))

    def match(self, stream):
        state = stream.state
        mark = stream.peek.mark
        values = []
        for pattern in self.patterns:
            result = pattern.match(stream)
            if result:
                values.append(result.value)
            else:
                stream.state = state
                return result
        return Success(mark, values)


@dataclass
class AllMap(Pattern):
    pattern: Pattern
    f: typing.Callable[[MatchResult], MatchResult]

    def match(self, stream):
        mark = stream.peek.mark
        result = self.pattern.match(stream)
        new_result = self.f(result)
        if not isinstance(new_result, MatchResult):
            raise Error(
                [mark],
                f'AllMap callback returned '
                f'non-MatchResult {repr(new_result)}')
        return new_result

    def __str__(self):
        return f'AllMap({self.pattern}, {self.f.__name__})'


@dataclass
class Forward(Pattern):
    name: str
    pattern: typing.Optional[Pattern] = None

    def match(self, stream):
        if self.pattern is None:
            raise base.Error(
                [stream.peek.mark],
                f'Forward pattern {self.name} used before being set',
            )

        return self.pattern.match(stream)

    def __str__(self):
        return f'{self.name}'


@dataclass
class Repeat(Pattern):
    pattern: Pattern
    min: int
    max: int

    def match(self, stream):
        mark = stream.peek.mark
        state = stream.state
        pattern = self.pattern
        values = []
        for _ in range(self.min):
            result = pattern.match(stream)
            if result:
                values.append(result.value)
            else:
                stream.state = state
                return result
        for _ in range(self.min, self.max):
            result = pattern.match(stream)
            if result:
                values.append(result.value)
            else:
                break
        return Success(mark, values)

    def __str__(self):
        return f'Repeat({self.pattern}, {self.min}, {self.max})'


@test.case
def test_sample_parser():
    @base.Lexer.new
    def lexer(lexer):
        @lexer.add('\s+')
        def spaces(m, mark):
            return ()

        @lexer.add('\w+')
        def name(m, mark):
            return [base.Token(mark, 'NAME', m.group())]

        @lexer.add('\(')
        def open_paren(m, mark):
            return [base.Token(mark, '(', m.group())]

        @lexer.add('\)')
        def close_paren(m, mark):
            return [base.Token(mark, ')', m.group())]

    sexpr = Forward('sexpr')
    atom = Any('NAME')
    expr = atom | sexpr
    prog = All(expr.repeat(), 'EOF').map(lambda args: args[0])

    sexpr.pattern = All('(', expr.repeat(), ')').map(lambda args: args[1])

    def parse(text):
        return prog.parse(lexer.lex_string(text))

    test.equal(
        parse("""
            (1)
            (begin
                (a b c)
            )
        """),
        Success(None, [['1'], ['begin', ['a', 'b', 'c']]])
    )

