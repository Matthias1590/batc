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
        self.top_levels = top_levels

@__pg.production("program : top_levels")
def __(xs):
    return Program(xs[0])


class TopLevel(Node):
    pass

__pg.production("top_levels : top_levels OTHR_NEWLINE top_level") \
    (__multiple_append)

__pg.production("top_levels : top_levels OTHR_NEWLINE") \
    (__first)

__pg.production("top_levels : top_level") \
    (__multiple_first)

__pg.production("top_levels : ") \
    (__multiple_empty)

__pg.production("top_level : var | func") \
    (__first)


class Func(TopLevel):
    def __init__(self, name: str, params: list[Param], return_type: Type, body: list[Statement]) -> None:
        self.name = name
        self.params = params
        self.return_type = return_type
        self.body = body

@__pg.production("func : KEYW_FUNC OTHR_IDENT SYMB_LPAREN params SYMB_RPAREN SYMB_ARROW type block")
def __(xs):
    return Func(xs[1].getstr(), xs[3], xs[6], xs[7])


class Param(Node):
    def __init__(self, name: str, type: Type) -> None:
        self.name = name
        self.type = type

__pg.production("params : params SYMB_COMMA param") \
    (__multiple_append)

__pg.production("params : param") \
    (__multiple_first)

__pg.production("params : ") \
    (__multiple_empty)

@__pg.production("param : OTHR_IDENT SYMB_COLON type")
def __(xs):
    return Param(xs[0].getstr(), xs[2])


class Statement(Node):
    pass

__pg.production("statements : statements OTHR_NEWLINE statement") \
    (__multiple_append)

__pg.production("statements : statements OTHR_NEWLINE") \
    (__first)

__pg.production("statements : statement") \
    (__multiple_first)

__pg.production("statements : ") \
    (__multiple_empty)

__pg.production("statement : var | expression | if | block") \
    (__first)


class Block(Statement):
    def __init__(self, statements: list[Statement]) -> None:
        self.statements = statements

@__pg.production("block : SYMB_LBRACE statements SYMB_RBRACE")
def __(xs):
    return Block(xs[1])


class If(Statement):
    def __init__(self, condition: Expression, then_body: Block, else_body: Block | If | None) -> None:
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body

@__pg.production("if : KEYW_IF expression block KEYW_ELSE block")
def __(xs):
    return If(xs[1], xs[3], xs[4])

@__pg.production("if : KEYW_IF expression block KEYW_ELSE if")
def __(xs):
    return If(xs[1], xs[2], xs[4])

@__pg.production("if : KEYW_IF expression block")
def __(xs):
    return If(xs[1], xs[2], None)

class Var(TopLevel):
    def __init__(self, name: str, type: Type, value: Expression | None) -> None:
        self.name = name
        self.type = type
        self.value = value

@__pg.production("var : KEYW_VAR OTHR_IDENT SYMB_COLON type SYMB_EQ expression")
def __(xs):
    return Var(xs[1].getstr(), xs[3], xs[5])

@__pg.production("var : KEYW_VAR OTHR_IDENT SYMB_COLON type")
def __(xs):
    return Var(xs[1].getstr(), xs[3])


class Type(Node):
    pass

class PrimitiveType(Type):
    pass

class VoidType(PrimitiveType):
    pass

class I8Type(PrimitiveType):
    pass

class U8Type(PrimitiveType):
    pass

class CharType(PrimitiveType):
    pass

class BoolType(PrimitiveType):
    pass

class PointerType(PrimitiveType):
    def __init__(self, type: Type) -> None:
        self.type = type

@__pg.production("type : TYPE_VOID")
def __(xs):
    return VoidType()

@__pg.production("type : TYPE_I8")
def __(xs):
    return I8Type()

@__pg.production("type : TYPE_U8")
def __(xs):
    return U8Type()

@__pg.production("type : TYPE_CHAR")
def __(xs):
    return CharType()

@__pg.production("type : TYPE_BOOL")
def __(xs):
    return BoolType()

@__pg.production("type : SYMB_STAR type")
def __(xs):
    return PointerType(xs[1])


class Expression(Node):
    pass

__pg.production("expression : literal | call | ident | deref | eqeq") \
    (__first)


class Deref(Expression):
    def __init__(self, expr: Expression) -> None:
        self.expr = expr

@__pg.production("deref : SYMB_STAR expression")
def __(xs):
    return Deref(xs[1])


class EqEq(Expression):
    def __init__(self, left: Expression, right: Expression) -> None:
        self.left = left
        self.right = right

@__pg.production("eqeq : expression SYMB_EQEQ expression")
def __(xs):
    return EqEq(xs[0], xs[2])


class Ident(Expression):
    def __init__(self, name: str) -> None:
        self.name = name

@__pg.production("ident : OTHR_IDENT")
def __(xs):
    return Ident(xs[0].getstr())


class Call(Expression):
    def __init__(self, name: str, args: list[Expression]) -> None:
        self.name = name
        self.args = args

@__pg.production("call : OTHR_IDENT SYMB_LPAREN args SYMB_RPAREN")
def __(xs):
    return Call(xs[0].getstr(), xs[2])


__pg.production("args : args SYMB_COMMA expression") \
    (__multiple_append)

__pg.production("args : expression") \
    (__multiple_first)

__pg.production("args : ") \
    (__multiple_empty)


class Literal(Expression):
    pass

class IntLiteral(Literal):
    def __init__(self, value: int) -> None:
        self.value = value

class StringLiteral(Literal):
    def __init__(self, value: str) -> None:
        self.value = value

class CharLiteral(Literal):
    def __init__(self, value: str) -> None:
        if len(value) != 1:
            raise ValueError("CharLiteral value must be exactly one character")

        self.value = value

@__pg.production("literal : LITR_INT")
def __(xs):
    return IntLiteral(int(xs[0].getstr()))

@__pg.production("literal : LITR_STRING")
def __(xs):
    return StringLiteral(xs[0].getstr()[1:-1].encode().decode("unicode_escape"))

@__pg.production("literal : LITR_CHAR")
def __(xs):
    return CharLiteral(xs[0].getstr()[1:-1].encode().decode("unicode_escape"))


__parser = __pg.build()

def parse(tokens: list[Token]) -> Node:
    return __parser.parse(iter(tokens))
