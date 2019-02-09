"""Parser combinator
"""
from . import base
from mtots import test
from mtots.util.dataclasses import dataclass
from typing import List, Tuple, Callable
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


class Parser(abc.ABC):

    @staticmethod
    def ensure_parser(s):
        if isinstance(s, Parser):
            return s
        elif isinstance(s, str):
            return Token(s)
        else:
            assert False, f'{repr(s)} is not a parser'

    def parse(self, tokens: typing.Iterable[base.Token]) -> MatchResult:
        return self.match(TokenStream(tokens))

    @abc.abstractmethod
    def match(self, stream: TokenStream) -> MatchResult:
        pass

    def allmap(self, f):
        """Creates a new parser that mutates the MatchResult with the
        given callback
        """
        return AllMap(self, [f])

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
class Token(Parser):
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


class CompoundParser(Parser):
    def __str__(self):
        return f'{type(self).__name__}({", ".join(map(str, self.parsers))})'


class Any(CompoundParser):
    def __init__(self, *parsers):
        _parsers = []
        for parser in parsers:
            if isinstance(parser, Any):
                _parsers.extend(parser.parsers)
            else:
                _parsers.append(Parser.ensure_parser(parser))
        self.parsers = tuple(_parsers)

    def match(self, stream):
        mark = stream.peek.mark
        result = Failure(mark, 'Zero parser Any')
        for parser in self.parsers:
            result = parser.match(stream)
            if result:
                return result
        return result


class All(CompoundParser):
    def __init__(self, *parsers):
        self.parsers = tuple(map(Parser.ensure_parser, parsers))

    def match(self, stream):
        state = stream.state
        mark = stream.peek.mark
        values = []
        for parser in self.parsers:
            result = parser.match(stream)
            if result:
                values.append(result.value)
            else:
                stream.state = state
                return result
        return Success(mark, values)


def _apply_callbacks(mark, result, callbacks):
    for f in callbacks:
        result = f(result)
        if not isinstance(result, MatchResult):
            raise Error(
                [mark],
                f'AllMap callback returned '
                f'non-MatchResult {repr(result)}')
    return result


@dataclass
class AllMap(Parser):
    parser: Parser
    callbacks: typing.List[typing.Callable[[MatchResult], MatchResult]]

    def __init__(self, parser, callbacks):
        if isinstance(parser, AllMap):
            self.parser = parser.parser
            self.callbacks = parser.callbacks + list(callbacks)
        else:
            self.parser = parser
            self.callbacks = callbacks

    def match(self, stream):
        mark = stream.peek.mark
        result = self.parser.match(stream)
        return _apply_callbacks(mark, result, self.callbacks)

    def __str__(self):
        return (
            f'AllMap({self.parser}, '
            f'{", ".join(f.__name__ for f in self.callbacks)})'
        )


@dataclass
class Forward(Parser):
    name: str

    @property
    def parser(self):
        return self._parser

    @parser.setter
    def parser(self, parser):
        self._parser = _handle_direct_left_recursion(self, parser)

    def match(self, stream):
        if self.parser is None:
            raise base.Error(
                [stream.peek.mark],
                f'Forward parser {self.name} used before being set',
            )

        return self.parser.match(stream)

    def __str__(self):
        return f'{self.name}'


def _handle_direct_left_recursion(fwd: Forward, parser):
    """
    We consider cases that look like

    A.parser = (
        All(A, B, C) |
        All(A, C) |
        All(x, Y) |
        x
    )

    A.parser = AllMap(Any([
        AllMap(All(A, ...), ...), ...
        AllMap(All(...), ...), ...
    ], ...)

    where 'A' is the fwd argument and 'A.parser' is the parser argument

    """
    original_parser = parser
    if isinstance(parser, AllMap):
        outer_callbacks = parser.callbacks
        parser = parser.parser
    else:
        outer_callbacks = ()

    if not isinstance(parser, Any):
        return original_parser

    alternatives = parser.parsers
    base_parsers: List[Parser] = []
    recurse_pairs: List[Tuple[
        Tuple[Parser, ...],
        Tuple[Callable[[TokenStream, MatchResult], MatchResult], ...]
    ]] = []

    for alternative in alternatives:
        if isinstance(alternative, AllMap):
            alt_callbacks = alternative.callbacks
            subparser = alternative.parser
        else:
            alt_callbacks = ()
            subparser = alternative

        if isinstance(subparser, All) and subparser.parsers[:1] == (fwd, ):
            if len(subparser.parsers) == 1:
                raise Error(
                    (),
                    f'Problematic reduction {fwd} -> {fwd}',
                )
            recurse_pairs.append((subparser.parsers[1:], alt_callbacks))
        else:
            base_parsers.append(alternative)

    if recurse_pairs:
        if not base_parsers:
            raise base.Error(
                [],
                f'non-terminal left recursion ({fwd.name})',
            )
        return _DirectLeftRecursive(
            f'{fwd.name}.left_recursive({parser})',
            Any(*base_parsers),
            outer_callbacks,
            tuple(recurse_pairs),
        )
    else:
        # If there's no left recursion, there's no need to
        # return anything different
        return original_parser


@dataclass
class _DirectLeftRecursive(Parser):
    name: str
    base_parser: Parser
    outer_callbacks: List[Callable[[MatchResult], MatchResult]]
    recurse_pairs: List[Tuple[
        Tuple[Parser, ...],
        Tuple[Callable[[MatchResult], MatchResult], ...]
    ]]

    def match(self, stream):
        mark = stream.peek.mark
        result = self.base_parser.match(stream)
        result = _apply_callbacks(mark, result, self.outer_callbacks)

        # WARNING: Pardon the spahgetti code...
        while result:
            state = stream.state
            mark = stream.peek.mark
            for postfix_parsers, alt_callbacks in self.recurse_pairs:
                subvalues = [result.value]
                failed = False
                for postfix_parser in postfix_parsers:
                    subresult = postfix_parser.match(stream)
                    if not subresult:
                        failed = True
                        break
                    subvalues.append(subresult.value)
                else:
                    # In this case, we've matched all the postfix parsers
                    # successfully.
                    # Now we want to apply the callbacks for succeeding.
                    new_result = _apply_callbacks(
                        mark,
                        Success(mark, subvalues),
                        alt_callbacks + self.outer_callbacks,
                    )
                    # The mappers could've caused the match to fail.
                    # If it didn't fail though, we can break
                    if new_result:
                        result = new_result
                        break
                # In this case, this set of postfix parsers and callbacks
                # could not complete successfullyself.
                # Rewind for a fresh next round.
                stream.state = state
            else:
                # If we tried all the recurse pairs, and we couldn't
                # find anything, there's no reason to be in this
                # while loop anymore.
                break
        return result

    def __str__(self):
        return self.name


@dataclass
class Repeat(Parser):
    parser: Parser
    min: int
    max: int

    def match(self, stream):
        mark = stream.peek.mark
        state = stream.state
        parser = self.parser
        values = []
        for _ in range(self.min):
            result = parser.match(stream)
            if result:
                values.append(result.value)
            else:
                stream.state = state
                return result
        for _ in range(self.min, self.max):
            result = parser.match(stream)
            if result:
                values.append(result.value)
            else:
                break
        return Success(mark, values)

    def __str__(self):
        return f'Repeat({self.parser}, {self.min}, {self.max})'


@base.Lexer.new
def test_lexer(lexer):
    @lexer.add('\s+')
    def spaces(m, mark):
        return ()

    @lexer.add('\w+')
    def name(m, mark):
        return [base.Token(mark, 'NAME', m.group())]

    @lexer.add('\+')
    def open_paren(m, mark):
        return [base.Token(mark, '+', m.group())]

    @lexer.add('\(')
    def open_paren(m, mark):
        return [base.Token(mark, '(', m.group())]

    @lexer.add('\)')
    def close_paren(m, mark):
        return [base.Token(mark, ')', m.group())]


@test.case
def test_sample_parser():
    sexpr = Forward('sexpr')
    atom = Any('NAME')
    expr = atom | sexpr
    prog = All(expr.repeat(), 'EOF').map(lambda args: args[0])

    sexpr.parser = All('(', expr.repeat(), ')').map(lambda args: args[1])

    def parse(text):
        return prog.parse(test_lexer.lex_string(text))

    test.equal(
        parse("""
            (1)
            (begin
                (a b c)
            )
        """),
        Success(None, [['1'], ['begin', ['a', 'b', 'c']]])
    )


@test.case
def test_left_recursive_grammar():
    atom = Any('NAME')
    addexpr = Forward('addexpr')
    expr = addexpr

    addexpr.parser = Any(
        All(addexpr, '+', atom),
        atom,
    )

    def parse(text):
        return expr.parse(test_lexer.lex_string(text))

    test.equal(
        parse("1 + 2 + 3"),
        Success(None, [['1', '+', '2'], '+', '3']),
    )


