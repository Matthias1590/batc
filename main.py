# pyright: reportShadowedImports=false

from lexer import lex
from parser import parse

with open("main_01.bat", "r") as f:
    source = f.read()

tokens = lex(source)

# for token in tokens:
#     print(token)

ast = parse(tokens)

print(ast)
