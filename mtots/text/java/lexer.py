"""Java lexer, mostly faithful to Java SE 11 spec

https://docs.oracle.com/javase/specs/jls/se11/html/jls-3.html

Some additional syntax for float literal and int literal
not yet done, are marked with TODO.
"""
from mtots import test
from mtots.text import base
import re


KEYWORDS = {
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
}

SEPARATORS = {
    '(', ')', '{', '}', '[', ']', ';', ',', '.', '...', '@', '::',
}


OPERATORS = {
    '=', '>', '<', '!', '~', '?', ':', '->',
    '==', '>=', '<=', '!=', '&&', '||', '++', '--',
    '+', '-', '*', '/', '&', '|', '^', '%', '<<', '>>', '>>>',
    '+=', '-=', '*=', '/=', '&=', '|=', '^=', '%=', '<<=', '>>=', '>>>=',
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

    @lexer.add(r'//.*?(?:\r|\n|\$)+')
    def line_comments(m, mark):
        return ()

    @lexer.add(r'/\*.*?\*/')
    def block_comments(m, mark):
        return ()

    @lexer.add(r'\bnull\b')
    def null_literal(m, mark):
        return [base.Token(mark, 'NULL', None)]

    @lexer.add(r'\btrue\b|\bfalse\b')
    def bool_literal(m, mark):
        value = m.group() == 'true'
        return [base.Token(mark, 'BOOL', value)]

    @lexer.add(r'(?:[^\W\d]|\$)(?:\w|\$)*')
    def id_or_keyword(m, mark):
        name = m.group()
        if name in KEYWORDS:
            return [base.Token(mark, name, None)]
        else:
            return [base.Token(mark, 'ID', name)]

    # TODO: Exponent part and Hex
    @lexer.add(r'(?:\d*\.\d+|\d+\.)(?:f|F|d|D)?')
    def float_literal(m, mark):
        text = m.group()
        if text.endswith(('f', 'F')):
            type = 'FLOAT'
        else:
            type = 'DOUBLE'
        value = float(text.strip('fFdD'))
        return [base.Token(mark, type, value)]

    # TODO: Hex, Octal, and Binary
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
                    raise base.Error([mark], f'Incomplete escape')
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
                    raise base.Error([mark], f'Invalid escape {s[i + 1]}')
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
        raise base.Error([mark], 'Multi-character char literal')

    separators_and_operators_regex = '|'.join(
        re.escape(symbol)
        for symbol in sorted(SEPARATORS | OPERATORS, reverse=True)
    )

    @lexer.add(separators_and_operators_regex)
    def separators_and_operators(m, mark):
        return [base.Token(mark, m.group(), None)]


def lex_string(s: str):
    return lexer.lex_string(s)


def lex(source: base.Source):
    return lexer.lex(source)


if __name__ == '__main__':
    lexer.main()


@test.case
def test_null():
    test.equal(
        list(lex_string('null')),
        [
            base.Token(None, 'NULL', None),
            base.Token(None, 'EOF', None),
        ]
    )


@test.case
def test_bool():
    test.equal(
        list(lex_string('true false')),
        [
            base.Token(None, 'BOOL', True),
            base.Token(None, 'BOOL', False),
            base.Token(None, 'EOF', None),
        ]
    )


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
        // this is a comment
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
        /* this is a comment
         * this is a block comment
         */
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
def test_sample_java_code():
    test.equal(
        list(lex_string(r"""
// Hi, this is some java code
package com.example.foo;

import java.util.ArrayList;

public final class Main {

    public static void main(String[] args) {
        System.out.println("Hello world!");
        ArrayList<Integer> arr = new ArrayList<>();
        System.out.println(arr);
    }
}
""")),
        [
            base.Token(None, 'package', None),
            base.Token(None, 'ID', 'com'),
            base.Token(None, '.', None),
            base.Token(None, 'ID', 'example'),
            base.Token(None, '.', None),
            base.Token(None, 'ID', 'foo'),
            base.Token(None, ';', None),
            base.Token(None, 'import', None),
            base.Token(None, 'ID', 'java'),
            base.Token(None, '.', None),
            base.Token(None, 'ID', 'util'),
            base.Token(None, '.', None),
            base.Token(None, 'ID', 'ArrayList'),
            base.Token(None, ';', None),
            base.Token(None, 'public', None),
            base.Token(None, 'final', None),
            base.Token(None, 'class', None),
            base.Token(None, 'ID', 'Main'),
            base.Token(None, '{', None),
            base.Token(None, 'public', None),
            base.Token(None, 'static', None),
            base.Token(None, 'void', None),
            base.Token(None, 'ID', 'main'),
            base.Token(None, '(', None),
            base.Token(None, 'ID', 'String'),
            base.Token(None, '[', None),
            base.Token(None, ']', None),
            base.Token(None, 'ID', 'args'),
            base.Token(None, ')', None),
            base.Token(None, '{', None),
            base.Token(None, 'ID', 'System'),
            base.Token(None, '.', None),
            base.Token(None, 'ID', 'out'),
            base.Token(None, '.', None),
            base.Token(None, 'ID', 'println'),
            base.Token(None, '(', None),
            base.Token(None, 'STR', 'Hello world!'),
            base.Token(None, ')', None),
            base.Token(None, ';', None),
            base.Token(None, 'ID', 'ArrayList'),
            base.Token(None, '<', None),
            base.Token(None, 'ID', 'Integer'),
            base.Token(None, '>', None),
            base.Token(None, 'ID', 'arr'),
            base.Token(None, '=', None),
            base.Token(None, 'new', None),
            base.Token(None, 'ID', 'ArrayList'),
            base.Token(None, '<', None),
            base.Token(None, '>', None),
            base.Token(None, '(', None),
            base.Token(None, ')', None),
            base.Token(None, ';', None),
            base.Token(None, 'ID', 'System'),
            base.Token(None, '.', None),
            base.Token(None, 'ID', 'out'),
            base.Token(None, '.', None),
            base.Token(None, 'ID', 'println'),
            base.Token(None, '(', None),
            base.Token(None, 'ID', 'arr'),
            base.Token(None, ')', None),
            base.Token(None, ';', None),
            base.Token(None, '}', None),
            base.Token(None, '}', None),
            base.Token(None, 'EOF', None),
        ],
    )
