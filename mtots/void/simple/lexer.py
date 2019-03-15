from . import errors
from mtots import test
from mtots.parser import base
import re


C_KEYWORDS = {
    'auto',
    'break',
    'case',
    'char',
    'const',
    'continue',
    'default',
    'do',
    'double',
    'else',
    'enum',
    'extern',
    'float',
    'for',
    'goto',
    'if',
    'inline', # (since C99)
    'int',
    'long',
    'register',
    'restrict', # (since C99)
    'return',
    'short',
    'signed',
    'sizeof',
    'static',
    'struct',
    'switch',
    'typedef',
    'union',
    'unsigned',
    'void',
    'volatile',
    'while',
    '_Alignas', # (since C11)
    '_Alignof', # (since C11)
    '_Atomic', # (since C11)
    '_Bool', # (since C99)
    '_Complex', # (since C99)
    '_Generic', # (since C11)
    '_Imaginary', # (since C99)
    '_Noreturn', # (since C11)
    '_Static_assert', # (since C11)
    '_Thread_local', # (since C11)
}

CXX_KEYWORDS = {
    'alignas',  # (since C++11)
    'alignof',  # (since C++11)
    'and',
    'and_eq',
    'asm',
    'atomic_cancel',  # (TM TS)
    'atomic_commit',  # (TM TS)
    'atomic_noexcept',  # (TM TS)
    'auto',  # (1)
    'bitand',
    'bitor',
    'bool',
    'break',
    'case',
    'catch',
    'char',
    'char8_t',  # (since C++20)
    'char16_t',  # (since C++11)
    'char32_t',  # (since C++11)
    'class',  # (1)
    'compl',
    'concept',  # (since C++20)
    'const',
    'consteval',  # (since C++20)
    'constexpr',  # (since C++11)
    'const_cast',
    'continue',
    'co_await',  # (coroutines TS)
    'co_return',  # (coroutines TS)
    'co_yield',  # (coroutines TS)
    'decltype',  # (since C++11)
    'default',  # (1)
    'delete',  # (1)
    'do',
    'double',
    'dynamic_cast',
    'else',
    'enum',
    'explicit',
    'export',  # (1)
    'extern',  # (1)
    'false',
    'float',
    'for',
    'friend',
    'goto',
    'if',
    'import',  # (modules TS)
    'inline',  # (1)
    'int',
    'long',
    'module',  # (modules TS)
    'mutable',  # (1)
    'namespace',
    'new',
    'noexcept',  # (since C++11)
    'not',
    'not_eq',
    'nullptr',  # (since C++11)
    'operator',
    'or',
    'or_eq',
    'private',
    'protected',
    'public',
    'reflexpr',  # (reflection TS)
    'register',  # (2)
    'reinterpret_cast',
    'requires',  # (since C++20)
    'return',
    'short',
    'signed',
    'sizeof',  # (1)
    'static',
    'static_assert',  # (since C++11)
    'static_cast',
    'struct',  # (1)
    'switch',
    'synchronized',  # (TM TS)
    'template',
    'this',
    'thread_local',  # (since C++11)
    'throw',
    'true',
    'try',
    'typedef',
    'typeid',
    'typename',
    'union',
    'unsigned',
    'using',  # (1)
    'virtual',
    'void',
    'volatile',
    'wchar_t',
    'while',
    'xor',
    'xor_eq',
}

KEYWORDS = {
    'def', 'var', 'import', 'native',

    # reserved
    'class', 'trait', 'new', 'delete', 'bool',
} | C_KEYWORDS | CXX_KEYWORDS

SYMBOLS = {
    '//',

    # C Punctuators
    '[', ']', '(', ')', '{', '}', '.', '->',
    '++', '--', '&', '*', '+', '-', '~', '!',
    '/', '%', '<<', '>>', '<', '>', '<=', '>=', '==', '!=', '^', '|',
        '&&', '||',
    '?', ':', ';', '...',
    '=', '*=', '/=', '%=', '+=', '-=', '<<=', '>>=', '&=', '^=', '|=',
    ',', '#', '##',
    '<:', ':>', '<%', '%>', '%:', '%:%:',
}

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
def lexer(lexer):

    @lexer.add(r'\s+')
    def skip_spaces(m, mark):
        return ()

    @lexer.add(r'\#.*?(?:\r|\n|$)+')
    def line_comments(m, mark):
        return ()

    @lexer.add(r'(?:[^\W\d]|\$)\w*')
    def id_or_keyword(m, mark):
        name = m.group()
        if name in KEYWORDS:
            return [base.Token(mark, name, None)]
        else:
            return [base.Token(mark, 'ID', name)]

    @lexer.add(r'`\w+`')
    def escaped_id(m, mark):
        # Allow user to specify valid C identifiers as identifiers.
        name = m.group()[1:-1]
        if name in C_KEYWORDS:
            raise errors.LexError(
                [mark],
                'C keywords cannot be used as identifiers even '
                f'if they are escaped ({name})',
            )
        return [base.Token(mark, 'ID', name)]

    @lexer.add(r'(?:\d*\.\d+|\d+\.)(?:f|F|d|D)?')
    def float_literal(m, mark):
        text = m.group()
        if text.endswith(('f', 'F')):
            type = 'FLOAT'
        else:
            type = 'DOUBLE'
        value = float(text.strip('fFdD'))
        return [base.Token(mark, type, value)]

    @lexer.add(r'(?:0|[1-9](?:_?\d)*)(?:l|L)?')
    def int_literal(m, mark):
        text = m.group()
        if text.endswith(('l', 'L')):
            type = 'LONG'
        else:
            type = 'INT'
        value = int(text.strip('lL'))
        return [base.Token(mark, type, value)]

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
                    raise errors.LexError([mark], f'Incomplete escape')
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
                    raise errors.LexError(
                        [mark],
                        f'Invalid escape {s[i + 1]}',
                    )
            else:
                j = i + 1
                while j < len(s) and s[j] != '\\':
                    j += 1
                parts.append(s[i:j])
                i = j
        return ''.join(parts)

    @lexer.add(r"'(?:" + escape_seq + r"|[^\r\n'])'")
    def char_literal(m, mark):
        value = resolve_str(m.group()[1:-1], mark)
        return [base.Token(mark, 'CHAR', value)]

    @lexer.add(r'"(?:' + escape_seq + r'|[^\r\n"])*"')
    def str_literal(m, mark):
        value = resolve_str(m.group()[1:-1], mark)
        return [base.Token(mark, 'STR', value)]

    @lexer.add(r"'(?:" + escape_seq + r"|[^\r\n'])*'")
    def invalid_char_literal(m, mark):
        raise errors.LexError([mark], 'Multi-character char literal')

    symbols_regex = '|'.join(
        re.escape(symbol)
        for symbol in sorted(SYMBOLS, reverse=True)
    )

    @lexer.add(symbols_regex)
    def separators_and_operators(m, mark):
        return [base.Token(mark, m.group(), None)]


def lex_string(s: str):
    return lexer.lex_string(s)


def lex(source: base.Source):
    return lexer.lex(source)


if __name__ == '__main__':
    lexer.main()


@test.case
def test_id():
    test.equal(
        list(lex_string('hi')),
        [
            base.Token(None, 'ID', 'hi'),
            base.Token(None, 'EOF', None),
        ]
    )


@test.case
def test_id():
    test.equal(
        list(lex_string('`hi`')),
        [
            base.Token(None, 'ID', 'hi'),
            base.Token(None, 'EOF', None),
        ]
    )
    test.equal(
        list(lex_string('`class`')),
        [
            base.Token(None, 'ID', 'class'),
            base.Token(None, 'EOF', None),
        ]
    )
    @test.throws(errors.LexError)
    def on_c_keyword():
        list(lex_string('`struct`'))


@test.case
def test_keyword():
    test.equal(
        list(lex_string('for')),
        [
            base.Token(None, 'for', None),
            base.Token(None, 'EOF', None),
        ]
    )


@test.case
def test_line_comment():
    test.equal(
        list(lex_string("""
        # this is a comment
        hi
        """)),
        [
            base.Token(None, 'ID', 'hi'),
            base.Token(None, 'EOF', None),
        ]
    )


@test.case
def test_block_comment():
    test.equal(
        list(lex_string("""
        # this is a comment
        # this is another comment
        hi
        """)),
        [
            base.Token(None, 'ID', 'hi'),
            base.Token(None, 'EOF', None),
        ]
    )


@test.case
def test_decimal_float():
    test.equal(
        list(lex_string("""
        1.0
        .5
        1.5f
        1.5F
        1.5D
        1.5d
        """)),
        [
            base.Token(None, 'DOUBLE', 1.0),
            base.Token(None, 'DOUBLE', 0.5),
            base.Token(None, 'FLOAT', 1.5),
            base.Token(None, 'FLOAT', 1.5),
            base.Token(None, 'DOUBLE', 1.5),
            base.Token(None, 'DOUBLE', 1.5),
            base.Token(None, 'EOF', None),
        ],
    )


@test.case
def test_decimal_int():
    test.equal(
        list(lex_string("""
        11l
        22L
        33
        44
        0
        """)),
        [
            base.Token(None, 'LONG', 11),
            base.Token(None, 'LONG', 22),
            base.Token(None, 'INT', 33),
            base.Token(None, 'INT', 44),
            base.Token(None, 'INT', 0),
            base.Token(None, 'EOF', None),
        ],
    )


@test.case
def test_string_and_char_literals():
    test.equal(
        list(lex_string(r"""
        "hi"
        'h'
        "h\nh"
        "\123"
        """)),
        [
            base.Token(None, 'STR', 'hi'),
            base.Token(None, 'CHAR', "h"),
            base.Token(None, 'STR', 'h\nh'),
            base.Token(None, 'STR', chr(int('123', 8))),
            base.Token(None, 'EOF', None),
        ],
    )


@test.case
def test_separators_and_operators():
    test.equal(
        list(lex_string(r"""
        ( ) , .
        +=
        +
        """)),
        [
            base.Token(None, '(', None),
            base.Token(None, ')', None),
            base.Token(None, ',', None),
            base.Token(None, '.', None),
            base.Token(None, '+=', None),
            base.Token(None, '+', None),
            base.Token(None, 'EOF', None),
        ],
    )


@test.case
def test_sample_code():
    test.equal(
        list(lex_string(r"""
# Hi, this is some code
import <stdio.h>

def main() int {
    printf("Hello world!\n");
    return 0;
}

""")),
        [
            base.Token(None, 'import', None),
            base.Token(None, '<', None),
            base.Token(None, 'ID', 'stdio'),
            base.Token(None, '.', None),
            base.Token(None, 'ID', 'h'),
            base.Token(None, '>', None),
            base.Token(None, 'def', None),
            base.Token(None, 'ID', 'main'),
            base.Token(None, '(', None),
            base.Token(None, ')', None),
            base.Token(None, 'int', None),
            base.Token(None, '{', None),
            base.Token(None, 'ID', 'printf'),
            base.Token(None, '(', None),
            base.Token(None, 'STR', 'Hello world!\n'),
            base.Token(None, ')', None),
            base.Token(None, ';', None),
            base.Token(None, 'return', None),
            base.Token(None, 'INT', 0),
            base.Token(None, ';', None),
            base.Token(None, '}', None),
            base.Token(None, 'EOF', None),
        ],
    )
