"""Parser combinator (DEPRECATED)

I still don't want to delete this, because there are some interesting
ideas here (e.g. support for direct left recursion).

However, in practice, using this library can be difficult to debug
because Python stack traces for complex grammars are basically useless
for debugging the grammars themselves.

If support for debugging grammars with some sort of stack trace is
ever added, this may become genuinely useful. Actually, for really simple
grammars, what is here is already fairly useful.

For now, the class mtots.text.base.Parser for making
hand-written recursive descent parsers is recommended.
"""
from . import base
from .base import Failure
from .base import MatchResult
from .base import Success
from .base import TokenStream
from mtots import test
from mtots.util.dataclasses import dataclass
from typing import Callable
from typing import Iterable
from typing import List
from typing import Tuple
import abc
import functools
import math
import operator
import typing


_INF = 1 << 62  # Effectively infinite integer


_sentinel = object()


class Parser(abc.ABC):

    @staticmethod
    def ensure_parser(s):
        if isinstance(s, Parser):
            return s
        elif isinstance(s, str):
            return Token(s)
        else:
            assert False, f'{repr(s)} is not a parser'

    def parse(self, tokens: Iterable[base.Token]) -> MatchResult:
        return self.match(TokenStream(tokens))

    @abc.abstractmethod
    def match(self, stream: TokenStream) -> MatchResult:
        pass

    def allmap(self, f):
        """Creates a new parser that mutates the MatchResult with the
        given callback
        """
        return AllMap(self, [f])

    def fatmap(self, f):
        """Fat map
        Like a reverse flatmap: feeds Success object as input to f,
        and expects f to return a value to add to new Success object.
        """

        @functools.wraps(f)
        def g(match_result):
            if match_result:
                return Success(match_result.mark, f(match_result))
            else:
                return match_result

        return self.allmap(g)

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

    def required(self):
        """Throw exception on failed match
        """

        def require(match):
            raise match.to_error()

        return self.recover(require)

    def map(self, f):

        @functools.wraps(f)
        def g(match_result):
            return Success(match_result.mark, f(match_result.value))

        return self.xmap(g)

    def valmap(self, value):
        return self.map(lambda x: value)

    def getitem(self, i):
        return self.map(operator.itemgetter(i))

    def flatten(self):

        def flatten(seq_of_seq):
            return [x for seq in seq_of_seq for x in seq]

        return self.map(flatten)

    def join(self, separator):
        return Any(
            All(
                self,
                All(separator, self).map(lambda args: args[1]).repeat(),
            ).map(lambda args: [args[0]] + args[1]),
            All(),
        )

    def repeat(self, min=0, max=_INF):
        return Repeat(self, min, max)

    def optional(self):
        return self.repeat(0, 1)

    def __or__(self, other):
        return Any(self, other)


@dataclass
class Token(Parser):
    type: str
    value: object = _sentinel

    def match(self, stream):
        peek = stream.peek
        mark = peek.mark
        if (peek.type == self.type and
                (self.value is _sentinel or peek.value == self.value)):
            return Success(mark, next(stream).value)
        elif self.value is _sentinel:
            return Failure(
                mark,
                f'Expected {self.type} but got {peek.type}',
            )
        else:
            return Failure(
                mark,
                f'Expected {self.type} (with value {self.value}) '
                f'but got {peek.type} ({peek.value})',
            )

    def __str__(self):
        return repr(self.type)


@dataclass
class Peek(Parser):
    """Try to parse with another parser, but unconditionally rewind
    regardless of success
    """
    def __init__(self, parser):
        self.parser = Parser.ensure_parser(parser)

    def match(self, stream):
        mark = stream.peek.mark
        state = stream.state
        result = self.parser.match(stream)
        stream.state = state
        return result

    def __str__(self):
        return repr(self.type)


class AnyTokenNotAt(Parser):
    """Accept any one token if the given parser does not match there"""
    def __init__(self, parser):
        self.parser = Parser.ensure_parser(parser)

    def match(self, stream):
        state = stream.state
        mark = stream.peek.mark
        result = self.parser.match(stream)
        stream.state = state
        if result:
            return Failure(
                mark,
                f'Expected any token not matching {self.parser}',
            )
        else:
            return Success(mark, next(stream).value)


def AnyTokenBut(*types):
    return AnyTokenNotAt(Any('EOF', *types))


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
        start_mark = stream.peek.mark
        last_mark = start_mark
        values = []
        for parser in self.parsers:
            result = parser.match(stream)
            if result:
                values.append(result.value)
                last_mark = result.mark
            else:
                stream.state = state
                return result
        mark = base.Mark(
            start_mark.source,
            start_mark.start,
            last_mark.end,
        )
        return Success(mark, values)


def Struct(constructor, patterns, *, include_mark=False):
    names = []
    raw_parsers = []
    for pattern in patterns:
        if isinstance(pattern, (str, Parser)):
            names.append(None)
            raw_parsers.append(Parser.ensure_parser(pattern))
        else:
            field_name, field_parser = pattern
            if field_name == 'mark' and include_mark:
                raise TypeError(
                    'include_mark is set to true, '
                    'but one of the fields is also named "mark"!')
            names.append(field_name)
            raw_parsers.append(Parser.ensure_parser(field_parser))

    parsers = [p.fatmap(lambda m: (m.mark, m.value)) for p in raw_parsers]

    def callback(m):
        kwargs = {
            key: val for key, (_m, val) in zip(names, m.value)
                if key is not None
        }
        if include_mark:
            # NOTE: The way that we determine the main index for the
            # mark associated with this construct may at first be
            # counter-intuitive, but is super effective for many cases.
            # The idea is to pick the location of the first sub-parser
            # that is unnamed.
            # If all subparsers are named, we default to using whatever
            # value 'All' thought was sensible.
            # Consider a few examples:
            # function call   <f> ( <args> )
            #  the first unnamed with the the '(' token.
            #  This is the one we want, since if we pointed to <f>,
            #  it would be unclear whether the mark pointed to the
            #  function call, or the expression that generated <f>
            #  itself.
            # binary operator    <a> + <b>
            #  the first (and only) unnamed token is the '+' token.
            #  Also good: if we pointed to <a> instead, it would be
            #  ambiguous whether the mark was pointed to just <a> or
            #  to <a> + <b> as a whole.
            #  By pointing to '+', there's no ambiguity.
            main_index = None
            for key, (val_mark, val) in zip(names, m.value):
                if key is None and main_index is None:
                    main_index = val_mark.i
                    break
            else:
                main_index = m.mark.main
            kwargs['mark'] = base.Mark(
                source=m.mark.source,
                start=m.mark.start,
                main=main_index,
                end=m.mark.end,
            )
        try:
            return constructor(**kwargs)
        except TypeError as e:
            raise TypeError(f'{constructor} construction failure') from e

    return All(*parsers).fatmap(callback)


def Required(pattern):
    return Any(pattern).required()


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
    callbacks: List[Callable[[MatchResult], MatchResult]]

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
    parser_factory: Callable[[], Parser]
    name: str = '<Forward>'
    _parser = None

    @property
    def parser(self):
        if self._parser is None:
            self._parser = _handle_direct_left_recursion(
                self,
                self.parser_factory(),
            )
            if not isinstance(self._parser, Parser):
                raise TypeError(
                    f'Forward parser is not a parser! '
                    f'({repr(self._parser)})',
                )
        return self._parser

    def match(self, stream):
        key = (stream.state, id(self))

        if key not in stream._cache:
            stream._cache[key] = None
            result = self._match_without_caching(stream)
            stream._cache[key] = (stream.state, result)
        elif stream._cache[key] is None:
            raise base.Error(
                [stream.peek.mark],
                f'Unsupported left recursion detected '
                f'while parsing at {stream.peek.mark.info} '
                f'{self.name} ({self.parser})',
            )

        stream.state, result = stream._cache[key]

        return result

    def _match_without_caching(self, stream):
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
    recurse_triples: List[Tuple[
        Tuple[Callable[[MatchResult], MatchResult], ...],
        Tuple[Parser, ...],
        Tuple[Callable[[MatchResult], MatchResult], ...],
    ]] = []

    for alternative in alternatives:
        if isinstance(alternative, AllMap):
            alt_callbacks = alternative.callbacks
            subparser = alternative.parser
        else:
            alt_callbacks = ()
            subparser = alternative

        if (isinstance(subparser, All) and
                len(subparser.parsers) >= 1 and
                (subparser.parsers[0] == fwd or
                    (isinstance(subparser.parsers[0], AllMap) and
                        subparser.parsers[0].parser == fwd))):
            if len(subparser.parsers) == 1:
                raise Error(
                    (),
                    f'Problematic reduction {fwd} -> {fwd}',
                )
            if isinstance(subparser.parsers[0], AllMap):
                first_callbacks = subparser.parsers[0].callbacks
            else:
                first_callbacks = ()
            recurse_triples.append((
                first_callbacks,
                subparser.parsers[1:],
                alt_callbacks,
            ))
        else:
            base_parsers.append(alternative)

    if recurse_triples:
        if not base_parsers:
            raise base.Error(
                [],
                f'non-terminal left recursion ({fwd.name})',
            )
        return _DirectLeftRecursive(
            f'{fwd.name}.left_recursive({parser})',
            Any(*base_parsers),
            outer_callbacks,
            tuple(recurse_triples),
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
    recurse_triples: List[Tuple[
        Tuple[Callable[[MatchResult], MatchResult], ...],
        Tuple[Parser, ...],
        Tuple[Callable[[MatchResult], MatchResult], ...],
    ]]

    def match(self, stream):
        start_mark = stream.peek.mark
        result = self.base_parser.match(stream)
        result = _apply_callbacks(result.mark, result, self.outer_callbacks)

        # WARNING: Pardon the spahgetti code...
        while result:
            state = stream.state
            middle_mark = stream.peek.mark
            for triple in self.recurse_triples:
                first_callbacks, postfix_parsers, alt_callbacks = triple
                first_callbacks_result = _apply_callbacks(
                    result.mark,
                    result,
                    first_callbacks,
                )
                if not first_callbacks_result:
                    # If any of the callbacks caused there to be
                    # a failure, this alternative has failed.
                    # We rewind for a fresh next round.
                    stream.state = state
                    continue
                subvalues = [first_callbacks_result.value]
                failed = False
                for postfix_parser in postfix_parsers:
                    subresult = postfix_parser.match(stream)
                    if not subresult:
                        failed = True
                        break
                    subvalues.append(subresult.value)
                    end_mark = subresult.mark
                else:
                    # In this case, we've matched all the postfix parsers
                    # successfully.
                    # Now we want to apply the callbacks for succeeding.
                    result_mark = base.Mark(
                        start_mark.source,
                        start_mark.start,
                        end_mark.end,
                        middle_mark.start,
                    )
                    new_result = _apply_callbacks(
                        result_mark,
                        Success(result_mark, subvalues),
                        tuple(alt_callbacks) + self.outer_callbacks,
                    )
                    # The mappers could've caused the match to fail.
                    # If it didn't fail though, we can break
                    if new_result:
                        result = new_result
                        break
                # In this case, this set of postfix parsers and callbacks
                # could not complete successfully.
                # Rewind for a fresh next round.
                stream.state = state
            else:
                # If we tried all the recurse triples, and we couldn't
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

    @lexer.add('\d+(\.\d*)?')
    def number(m, mark):
        return [base.Token(mark, 'NUMBER', float(m.group()))]

    @lexer.add('\w+')
    def name(m, mark):
        return [base.Token(mark, 'NAME', m.group())]

    @lexer.add('\+|\-|\*|\/|\%|\,')
    def open_paren(m, mark):
        return [base.Token(mark, m.group(), m.group())]

    @lexer.add('\(')
    def open_paren(m, mark):
        return [base.Token(mark, '(', m.group())]

    @lexer.add('\)')
    def close_paren(m, mark):
        return [base.Token(mark, ')', m.group())]


@test.case
def test_sample_parser():
    sexpr = Forward(
        name='sexpr',
        parser_factory=(
            lambda: All('(', expr.repeat(), ')').map(lambda args: args[1])
        ),
    )
    atom = Any('NAME', 'NUMBER')
    expr = atom | sexpr
    prog = All(expr.repeat(), 'EOF').map(lambda args: args[0])

    def parse(text):
        return prog.parse(test_lexer.lex_string(text))

    test.equal(
        parse("""
            (1)
            (begin
                (a b c)
            )
        """),
        Success(None, [[1], ['begin', ['a', 'b', 'c']]])
    )


@test.case
def test_left_recursive_grammar():
    atom = Any('NAME', 'NUMBER')
    addexpr = Forward(name='addexpr', parser_factory=lambda: Any(
        All(addexpr, '+', atom),
        atom,
    ))
    expr = addexpr

    def parse(text):
        return expr.parse(test_lexer.lex_string(text))

    test.equal(
        parse("1 + 2 + 3"),
        Success(None, [[1, '+', 2], '+', 3]),
    )


@test.case
def test_simple_arithmetic_grammar():
    expr = Forward(name='expr', parser_factory=lambda: addexpr)
    atom = Any('NUMBER', All('(', expr, ')').map(lambda args: args[1]))
    mulexpr = Forward(name='mulexpr', parser_factory=lambda: (
        All(mulexpr, '*', atom).map(lambda args: args[0] * args[2]) |
        All(mulexpr, '/', atom).map(lambda args: args[0] / args[2]) |
        All(mulexpr, '%', atom).map(lambda args: args[0] % args[2]) |
        atom
    ))
    addexpr = Forward(name='addexpr', parser_factory=lambda: (
        All(addexpr, '+', mulexpr).map(lambda args: args[0] + args[2]) |
        All(addexpr, '-', mulexpr).map(lambda args: args[0] - args[2]) |
        mulexpr
    ))

    def parse(text):
        return expr.parse(test_lexer.lex_string(text))

    test.equal(
        parse('1 + 2 - 7 * 2'),
        Success(None, 1 + 2 - 7 * 2),
    )

    test.equal(
        parse('1 + (2 - 7) * 2'),
        Success(None, 1 + (2 - 7) * 2),
    )


@test.case
def test_join():
    expr = Forward(name='expr', parser_factory=lambda: addexpr)
    atom = Any('NUMBER', All('(', expr, ')').map(lambda args: args[1]))
    mulexpr = Forward(name='mulexpr', parser_factory=lambda: (
        All(mulexpr, '*', atom).map(lambda args: args[0] * args[2]) |
        All(mulexpr, '/', atom).map(lambda args: args[0] / args[2]) |
        All(mulexpr, '%', atom).map(lambda args: args[0] % args[2]) |
        atom
    ))
    addexpr = Forward(name='addexpr', parser_factory=lambda: (
        All(addexpr, '+', mulexpr).map(lambda args: args[0] + args[2]) |
        All(addexpr, '-', mulexpr).map(lambda args: args[0] - args[2]) |
        mulexpr
    ))
    expr_list = All('(', expr.join(','), ')').map(lambda args: args[1])

    def parse(text):
        return expr_list.parse(test_lexer.lex_string(text))

    test.equal(
        parse('()'),
        Success(None, []),
    )

    test.equal(
        parse('(1, 1 + 2)'),
        Success(None, [1, 3]),
    )

    test.equal(
        parse('(4 + 4 * 65, 2, 3.4)'),
        Success(None, [264, 2, 3.4]),
    )

    test.equal(
        parse('(5)'),
        Success(None, [5]),
    )


@test.case
def test_struct():
    class Foo(typing.NamedTuple):
        abc: float
        xyz: str

    foo_parser = Struct(Foo, [
        ['abc', 'NUMBER'],
        '+',
        ['xyz', 'NAME'],
    ])

    def parse(parser, text):
        return parser.parse(test_lexer.lex_string(text))

    test.equal(
        parse(foo_parser, "924 + hi"),
        Success(None, Foo(924, 'hi')),
    )

    class Bar(typing.NamedTuple):
        mark: base.Mark
        abc: float
        xyz: str

    bar_parser = Struct(Bar, [
        ['abc', 'NUMBER'],
        '+',
        ['xyz', 'NAME'],
    ], include_mark=True)

    m = parse(bar_parser, "924 + hi")
    test.that(isinstance(m.mark, base.Mark))
    test.that(isinstance(m, Success))
    test.that(hasattr(m.value, 'mark'))
    test.equal(
        m,
        Success(None, Bar(m.value.mark, 924, 'hi')),
    )

