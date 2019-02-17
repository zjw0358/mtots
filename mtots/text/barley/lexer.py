"""Java lexer, mostly faithful to Java SE 11 spec

https://docs.oracle.com/javase/specs/jls/se11/html/jls-3.html

Some additional syntax for float literal and int literal
not yet done, are marked with TODO.
"""
from mtots import test
from mtots.text import base
import re


KEYWORDS = {
    'true', 'false',
    'trait',

    # Reserved
    'null', 'nil',

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
        raw_indent = m.group()[1:]
        return [base.Token(mark, 'NEWLINE', raw_indent)]

    @builder.add(r'[^\S\n]+')
    def skip_spaces(m, mark):
        return ()

    @builder.add(r'#.*?(?=\r|\n|\$)')
    def line_comments(m, mark):
        return ()

    @builder.add(r'(?:[^\W\d]|\$)(?:\w|\$)*')
    def id_or_keyword(m, mark):
        name = m.group()
        if name in KEYWORDS:
            return [base.Token(mark, name, None)]
        else:
            return [base.Token(mark, 'ID', name)]

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

    @builder.add(r"'(?:" + escape_seq + r"|[^\r\n'])*'")
    def single_quote_str_literal(m, mark):
        value = resolve_str(m.group()[1:-1], mark)
        return [base.Token(mark, 'STR', value)]

    @builder.add(r'"(?:' + escape_seq + r'|[^\r\n"])*"')
    def double_quote_str_literal(m, mark):
        value = resolve_str(m.group()[1:-1], mark)
        return [base.Token(mark, 'STR', value)]

    symbols_regex = '|'.join(map(re.escape, SYMBOLS))

    @builder.add(symbols_regex)
    def separators_and_operators(m, mark):
        return [base.Token(mark, m.group(), None)]

    @builder.add_adapter
    def remove_nested_newlines_adapter(tokens):
        depth = 0
        openers = ('(', '{', '[')
        closers = (']', '}', ')')
        for token in tokens:
            if token.type in openers:
                depth += 1
            elif token.type in closers:
                depth -= 1
            elif token.type == 'NEWLINE' and depth > 0:
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

    @builder.add_adapter
    def process_indents_adapter(tokens):
        stack = ['']
        for token in tokens:

            if token.type == 'EOF':
                while len(stack) > 1:
                    stack.pop()
                    yield base.Token(token.mark, 'DEDENT', None)

            if token.type == 'NEWLINE':
                yield base.Token(token.mark, 'NEWLINE', None)
                indent = token.value
                if indent != stack[-1]:
                    if indent.startswith(stack[-1]):
                        yield base.Token(token.mark, 'INDENT', None)
                        stack.append(indent)
                    elif stack[-1].startswith(indent):
                        while (stack[-1] != indent and
                                stack[-1].startswith(indent)):
                            stack.pop()
                            yield base.Token(token.mark, 'DEDENT', None)
                if indent != stack[-1]:
                    raise base.Error([token.mark], 'Invalid indent')
            else:
                yield token


def lex_string(s: str):
    return lexer.lex_string(s)


def lex(source: base.Source):
    return lexer.lex(source)


if __name__ == '__main__':
    lexer.main()


@test.case
def test_sample_simple_python_code():
    test.equal(
        list(lex_string(r"""
# Some comments
def foo(

        ):
    pass
""")),
        [
            base.Token(None, 'NEWLINE', None),
            base.Token(None, 'def', None),
            base.Token(None, 'ID', 'foo'),
            base.Token(None, '(', None),
            base.Token(None, ')', None),
            base.Token(None, ':', None),
            base.Token(None, 'NEWLINE', None),
            base.Token(None, 'INDENT', None),
            base.Token(None, 'pass', None),
            base.Token(None, 'NEWLINE', None),
            base.Token(None, 'DEDENT', None),
            base.Token(None, 'EOF', None),
        ],
    )


@test.case
def test_eof_dedents():
    test.equal(
        list(lex_string(r"""
foo
    bar""")),
        [
            base.Token(None, 'NEWLINE', None),
            base.Token(None, 'ID', 'foo'),
            base.Token(None, 'NEWLINE', None),
            base.Token(None, 'INDENT', None),
            base.Token(None, 'ID', 'bar'),
            base.Token(None, 'DEDENT', None),
            base.Token(None, 'EOF', None),
        ],
    )
