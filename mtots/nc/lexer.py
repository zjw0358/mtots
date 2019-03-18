"""Lexer that supports Python-style syntax
including INDENT/DEDENT tokens, NEWLINE tokens,
and excluding NEWLINE tokens when they appear inside (), [] or {}
groupings.
"""
from . import errors
from mtots import test
from mtots.parser import base
import re


KEYWORDS = {
    'true', 'false',
    'class', 'var', 'def',
    'string', 'tuple',
    'inline',

    # Reserved
    'null', 'nil', 'trait', 'struct',

    # Java keywords
    'abstract', 'continue', 'for', 'new', 'switch',
    'assert', 'default', 'if', 'package', 'synchronized',
    'boolean', 'do', 'goto', 'private', 'this',
    'break', 'double', 'implements', 'protected', 'throw',
    'byte', 'else', 'import', 'public', 'throws',
    'case', 'enum', 'instanceof', 'return', 'transient',
    'catch', 'extends', 'int', 'short', 'try',
    'char', 'final', 'interface', 'static', 'void',
    'class', 'finally', 'long', 'strictfp', 'volatile',
    'const', 'float', 'native', 'super', 'while',
    '_',

    # Python keywords
    'False', 'await', 'else', 'import', 'pass',
    'None', 'break', 'except', 'in', 'raise',
    'True', 'class', 'finally', 'is', 'return',
    'and', 'continue', 'for', 'lambda', 'try',
    'as', 'def', 'from', 'nonlocal', 'while',
    'assert', 'del', 'global', 'not', 'with',
    'async', 'elif', 'if', 'or', 'yield',
}

SYMBOLS = tuple(sorted({

    # Python operators
    '+', '-', '*', '**', '/', '//', '%', '@',
    '<<', '>>', '&', '|', '^', '~',
    '<', '>', '<=', '>=', '==', '!=',

    # Python delimiters
    '(', ')', '[', ']', '{', '}',
    ',', ':', '.', ';', '@', '=', '->',
    '+=', '-=', '*=', '/=', '//=', '%=', '@=',
    '&=', '|=', '^=', '>>=', '<<=', '**=',

    # Python reserved symbols
    '$', '?', '`',

    # Java delimieters
    '(', ')', '{', '}', '[', ']', ';', ',', '.', '...', '@', '::',

    # Java operators
    '=', '>', '<', '!', '~', '?', ':', '->',
    '==', '>=', '<=', '!=', '&&', '||', '++', '--',
    '+', '-', '*', '/', '&', '|', '^', '%', '<<', '>>', '>>>',
    '+=', '-=', '*=', '/=', '&=', '|=', '^=', '%=', '<<=', '>>=', '>>>=',
}, reverse=True))

_ESCAPE_MAP = {
    'b': '\b',
    't': '\t',
    'n': '\n',
    'f': '\f',
    'r': '\r',
    '\"': '\"',
    '\'': '\'',
    '\\': '\\',
}


@base.Lexer.new
def lexer(builder):

    @builder.add(r'\n[^\S\n]*')
    def newline_and_raw_indent(m, mark):
        return [base.Token(mark, 'NEWLINE', None)]

    @builder.add(r'[^\S\n]+')
    def skip_spaces(m, mark):
        return ()

    @builder.add(r'#.*?(?=\r|\n|\$)')
    def line_comments(m, mark):
        return ()

    @builder.add(r'(?:\d*\.\d+|\d+\.)')
    def float_literal(m, mark):
        text = m.group()
        return [base.Token(mark, 'FLOAT', float(text))]

    @builder.add(r'(?:0|[1-9](?:_?\d)*)')
    def int_literal(m, mark):
        text = m.group()
        return [base.Token(mark, 'INT', int(text))]

    escape_seq = (
        '|'.join(f'\\{c}' for c in _ESCAPE_MAP)
        + r'|\[0-3][0-7][0-7]'
        + r'|\[0-7][0-7]'
        + r'|\[0-7]'
    )

    def resolve_str(s, mark):
        parts = []
        i = 0
        while i < len(s):
            if s[i] == '\\':
                if i + 1 >= len(s):
                    raise errors.InvalidEscape(
                        [mark], f'Incomplete escape')
                if s[i + 1].isdigit():
                    j = i + 1
                    while j < len(s) and s[j].isdigit():
                        j += 1
                    parts.append(chr(int(s[i + 1:j], 8)))
                    i = j
                elif s[i + 1] in _ESCAPE_MAP:
                    parts.append(_ESCAPE_MAP[s[i + 1]])
                    i += 2
                else:
                    raise errors.InvalidEscape(
                        [mark], f'Invalid escape {s[i + 1]}')
            else:
                j = i + 1
                while j < len(s) and s[j] != '\\':
                    j += 1
                parts.append(s[i:j])
                i = j
        return ''.join(parts)

    @builder.add(r'r"""(?:(?!""").)*?"""')
    def triple_double_quote_raw_str_literal(m, mark):
        value = m.group()[4:-3]
        return [base.Token(mark, 'STR', value)]

    @builder.add(r"r'''(?:(?!''').)*?'''")
    def triple_single_quote_raw_str_literal(m, mark):
        value = m.group()[4:-3]
        return [base.Token(mark, 'STR', value)]

    @builder.add(r'"""(?:' + escape_seq + r'|(?!""").)*?"""')
    def triple_double_quote_str_literal(m, mark):
        value = resolve_str(m.group()[3:-3], mark)
        return [base.Token(mark, 'STR', value)]

    @builder.add(r"'''(?:" + escape_seq + r"|(?!''').)*?'''")
    def triple_single_quote_str_literal(m, mark):
        value = resolve_str(m.group()[3:-3], mark)
        return [base.Token(mark, 'STR', value)]

    @builder.add(r"'(?:" + escape_seq + r"|[^\r\n'])*'")
    def single_quote_str_literal(m, mark):
        value = resolve_str(m.group()[1:-1], mark)
        return [base.Token(mark, 'STR', value)]

    @builder.add(r'"(?:' + escape_seq + r'|[^\r\n"])*"')
    def double_quote_str_literal(m, mark):
        value = resolve_str(m.group()[1:-1], mark)
        return [base.Token(mark, 'STR', value)]

    @builder.add(r"'(?:[^\r\n'])*'")
    def single_quote_raw_str_literal(m, mark):
        value = m.group()[2:-1]
        return [base.Token(mark, 'STR', value)]

    @builder.add(r'"(?:[^\r\n"])*"')
    def double_quote_raw_str_literal(m, mark):
        value = m.group()[2:-1]
        return [base.Token(mark, 'STR', value)]

    symbols_regex = '|'.join(map(re.escape, SYMBOLS))

    @builder.add(symbols_regex)
    def separators_and_operators(m, mark):
        return [base.Token(mark, m.group(), None)]

    @builder.add(r'(?:[^\W\d]|\$)(?:\w|\$)*')
    def id_or_keyword(m, mark):
        name = m.group()
        if name in KEYWORDS:
            return [base.Token(mark, name, None)]
        else:
            return [base.Token(mark, 'ID', name)]

    def should_skip_newline(stack):
        return stack and stack[-1].type != '{'

    @builder.add_adapter
    def remove_nested_newlines_adapter(tokens):
        grouping_map = {
            '(': ')',
            '{': '}',
            '[': ']',
        }
        openers = tuple(grouping_map.keys())
        closers = tuple(grouping_map.values())
        stack = []
        for token in tokens:
            if token.type in openers:
                stack.append(token)
            elif token.type in closers:
                if not stack:
                    raise errors.InvalidGrouping(
                        [token.mark], f'Unmatched closing symbol')
                opener = stack.pop()
                if grouping_map[opener.type] != token.type:
                    raise errors.InvalidGrouping(
                        [opener.mark, token.mark],
                        f'Mismatched grouping symbols')
            elif token.type == 'NEWLINE' and should_skip_newline(stack):
                continue
            yield token

    @builder.add_adapter
    def remove_consecutive_newlines_adapter(tokens):
        try:
            while True:
                last_token = next(tokens)
                if last_token.type == 'NEWLINE':
                    token = next(tokens)
                    while token.type == 'NEWLINE':
                        last_token = token
                        token = next(tokens)
                    yield last_token
                    yield token
                else:
                    yield last_token
        except StopIteration:
            pass


def lex_string(s: str):
    return lexer.lex_string(s)


def lex(source: base.Source):
    return lexer.lex(source)


if __name__ == '__main__':
    lexer.main()


@test.case
def test_empty():
    test.equal(
        list(lex_string(r"""
        """)),
        [base.Token(None, 'NEWLINE', None), base.Token(None, 'EOF', None)],
    )


@test.case
def test_newline_and_grouping():
    # Newlines should only appear:
    #  * at top level,
    #  * or inside '{}' grouping symbol
    test.equal(
        list(lex_string(r"""
        (
        )[
        ]{
        }""")),
        [
            base.Token(None, 'NEWLINE', None),
            base.Token(None, '(', None),
            base.Token(None, ')', None),
            base.Token(None, '[', None),
            base.Token(None, ']', None),
            base.Token(None, '{', None),
            base.Token(None, 'NEWLINE', None),
            base.Token(None, '}', None),
            base.Token(None, 'EOF', None),
        ],
    )
    test.equal(
        list(lex_string(r"""({
        })""")),
        [
            base.Token(None, '(', None),
            base.Token(None, '{', None),
            base.Token(None, 'NEWLINE', None),
            base.Token(None, '}', None),
            base.Token(None, ')', None),
            base.Token(None, 'EOF', None),
        ],
    )

    @test.throws(errors.InvalidGrouping)
    def throws():
        list(lex_string('( ]'))

    @test.throws(errors.InvalidGrouping)
    def throws():
        list(lex_string(']'))

    list(lex_string('[ ]'))


@test.case
def test_triple_quote():
    test.equal(
        list(lex_string(r'''(
            """hi""" """world"""
        )''')),
        [
            base.Token(None, '(', None),
            base.Token(None, 'STR', 'hi'),
            base.Token(None, 'STR', 'world'),
            base.Token(None, ')', None),
            base.Token(None, 'EOF', None),
        ],
    )
    test.equal(
        list(lex_string(r"""(
            '''hi''' '''world'''
        )""")),
        [
            base.Token(None, '(', None),
            base.Token(None, 'STR', 'hi'),
            base.Token(None, 'STR', 'world'),
            base.Token(None, ')', None),
            base.Token(None, 'EOF', None),
        ],
    )
