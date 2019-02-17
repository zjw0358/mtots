from . import fwd_ast as ast
from . import lexer
from mtots import test
from mtots.text import base


@base.Parser.new
def parser(builder):
    pass


# def _parse_string(s):
#     tokens = lexer.lex_string(s)
#     return parser.parse(tokens)
#
#
# @test.case
# def test_sample():
#     r = _parse_string("""int foo
#     pass
# """)
#     print(r)
