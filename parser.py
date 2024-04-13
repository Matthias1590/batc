# pyright: reportShadowedImports=false

from __future__ import annotations
from rply import ParserGenerator
from lexer import TokenType, Token

__pg = ParserGenerator([t._name_ for t in TokenType])


class Node:
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({', '.join(f'{k}={v!r}' for k, v in self.__dict__.items() if not k.startswith('_'))})"

def __multiple_append(xs):
    return xs[0] + [xs[-1]]

def __multiple_first(xs):
    return [xs[0]]

def __multiple_empty(xs):
    return []

def __first(xs):
    return xs[0]


class Program(Node):
    def __init__(self, top_levels: list[TopLevel]) -> None:
        self.__top_levels = top_levels

@__pg.production("program : top_levels")
def __(xs):
    return Program(xs[0])


class TopLevel(Node):
    pass

__pg.production("top_levels : top_levels OTHR_NEWLINE top_level") \
    (__multiple_append)

__pg.production("top_levels : top_level") \
    (__multiple_first)

__pg.production("top_levels : ") \
    (__multiple_empty)

__pg.production("top_level : var") \
    (__first)


class Var(TopLevel):
    def __init__(self, name: str, type: Type, value: Expression) -> None:
        self.__name = name
        self.__type = type
        self.__value = value
    
@__pg.production("var : KEYW_VAR OTHR_IDENT SYMB_COLON type SYMB_EQ expression")
def __(xs):
    return Var(xs[1].getstr(), xs[3], xs[5])


class Type(Node):
    pass


__parser = __pg.build()

def parse(tokens: list[Token]) -> Node:
    return __parser.parse(iter(tokens))
