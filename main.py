# pyright: reportShadowedImports=false

from lexer import lex
from parser import parse, Scope

with open("main.bat", "r") as f:
    source = f.read()

tokens = lex(source)

ast = parse(tokens)

ast.scope = Scope()
ast.declare()
ast.check()
asm = ast.compile()

with open("main.asm", "w") as f:
    f.write(asm)
