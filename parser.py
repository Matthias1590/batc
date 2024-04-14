# pyright: reportShadowedImports=false

from __future__ import annotations
from rply import ParserGenerator
from lexer import TokenType, Token
import time

__pg = ParserGenerator([t._name_ for t in TokenType], [
    # TODO: Add precedence for other operators
    ("left", ["SYMB_EQEQ"]),
    ("left", ["SYMB_STAR"])
])

BASE_POINTER_REG = 7
STACK_POINTER_REG = 6

HEAP_END = 128
STATIC_MEMORY_SIZE = 64
STACK_END = HEAP_END + STATIC_MEMORY_SIZE

def repr_immediate(x: int) -> str:
    return f"#{x}"

def repr_register(x: int) -> str:
    if isinstance(x, RegisterDestination):
        return repr(x)

    return f"r{x}"

def repr_offset(x: int) -> str:
    if x < -32 or x > 31:
        raise ValueError(f"Offset {x} out of range")

    return repr_immediate(x)

def repr_user_label(x: str) -> str:
    return f".user_{x}"

def repr_temp_label() -> str:
    return f".temp_{time.time()}"

def repr_batc_label(x: str) -> str:
    return f".batc_{x}"


class Destination:
    def load_from_register(self, register: int) -> str:
        raise NotImplementedError(self.__class__.__name__)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({', '.join(f'{k}={v!r}' for k, v in self.__dict__.items() if not k.startswith('_'))})"

class RegisterDestination(Destination):
    def __init__(self, register: int, scope: Scope | None = None) -> None:
        self.register = register
        self.scope = scope

    def __repr__(self) -> str:
        return repr_register(self.register)

    def __enter__(self):
        if self.scope is None:
            raise ValueError("RegisterDestination must be used within a scope")

        return self

    def __exit__(self, *_):
        self.scope.regs.add(self.register)

class MemoryDestination(Destination):
    def __init__(self, address: int) -> None:
        self.address = address

class RegisterOffsetDestination(MemoryDestination):
    def __init__(self, register: int, offset: int) -> None:
        self.register = register
        self.offset = offset

    def load_from_register(self, register: int) -> str:
        return f"mst {repr_register(self.register)}, {repr_offset(self.offset)}, {repr_register(register)}"

    def __repr__(self) -> str:
        return f"{repr_register(self.register)}, {repr_offset(self.offset)}"


class Scope:
    def __init__(self, parent: Scope | None = None) -> None:
        self.parent = parent
        self.vars = {}
        self.addrs = {}
        self.offset = 0

        if self.parent is None:
            self.init_top_level()

    def init_top_level(self) -> None:
        self.regs = set(range(2, 6))

        self.declare_func("write_port", [U8Type(), U8Type()], VoidType())
        self.declare_func("read_port", [U8Type()], U8Type())

    def alloc_register(self) -> RegisterDestination:
        if self.parent is not None:
            return self.parent.alloc_register()

        if len(self.regs) == 0:
            raise ValueError("Out of registers")

        return RegisterDestination(self.regs.pop(), self)


    def declare_var(self, name: str, type: Type) -> None:
        if name in self.vars:
            raise ValueError(f"Redefinition of symbol {name!r}")

        self.vars[name] = type
        if self.parent is not None:
            self.addrs[name] = RegisterOffsetDestination(BASE_POINTER_REG, self.offset)
        else:
            addr = STACK_END - 1 - self.offset
            if addr <= HEAP_END:
                raise ValueError("Out of static memory")

            self.addrs[name] = MemoryDestination(addr)
        self.offset += 1

    def declare_func(self, name: str, param_types: list[Type], return_type: Type) -> None:
        if self.parent is not None:
            raise ValueError("Functions can only be declared at the top level")

        if name in self.vars:
            raise ValueError(f"Redefinition of symbol {name!r}")

        self.vars[name] = (param_types, return_type)

    def get_func(self, name: str) -> tuple[list[Type], Type]:
        if name not in self.vars:
            if self.parent is not None:
                return self.parent.get_func(name)
            raise ValueError(f"Function {name!r} not declared")

        if not isinstance(self.vars[name], tuple):
            raise Exception(f"Symbol {name!r} is not a function")

        return self.vars[name]

    def get_var_type(self, name: str) -> Type:
        if name not in self.vars:
            if self.parent is not None:
                return self.parent.get_var_type(name)
            raise ValueError(f"Symbol {name!r} not declared")

        return self.vars[name]

    def get_var_address(self, name: str) -> Destination:
        if name not in self.vars:
            if self.parent is not None:
                return self.parent.get_var_address(name)
            raise ValueError(f"Symbol {name!r} not declared")

        return self.addrs[name]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({', '.join(f'{k}={v!r}' for k, v in self.__dict__.items() if not k.startswith('_'))})"

class Node:
    scope: Scope

    def declare(self) -> None:
        raise NotImplementedError(self.__class__.__name__)

    def compile(self) -> str:
        raise NotImplementedError(self.__class__.__name__)

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

    def declare(self) -> None:
        for top_level in self.top_levels:
            top_level.scope = self.scope
            top_level.declare()

    def check(self) -> None:
        for top_level in self.top_levels:
            top_level.check()

    def compile(self) -> str:
        with open("runtime.asm", "r") as f:
            runtime = f.read()

        return runtime + "\n".join(top_level.compile() for top_level in self.top_levels)

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
    def __init__(self, name: str, params: list[Param], return_type: Type, body: Block) -> None:
        self.name = name
        self.params = params
        self.return_type = return_type
        self.body = body

    def declare(self) -> None:
        self.scope.declare_func(self.name, [p.type for p in self.params], self.return_type)

        self.body.scope = Scope(self.scope)

        for param in self.params:
            param.scope = self.body.scope
            param.declare()

        self.body.declare()

    def check(self) -> None:
        self.body.check()

    def compile(self) -> str:
        return f"{repr_user_label(self.name)}\n" + self.body.compile()

@__pg.production("func : KEYW_FUNC OTHR_IDENT SYMB_LPAREN params SYMB_RPAREN SYMB_ARROW type block")
def __(xs):
    return Func(xs[1].getstr(), xs[3], xs[6], xs[7])


class Param(Node):
    def __init__(self, name: str, type: Type) -> None:
        self.name = name
        self.type = type

    def declare(self) -> None:
        self.scope.declare_var(self.name, self.type)

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

    def declare(self) -> None:
        for statement in self.statements:
            statement.scope = self.scope
            statement.declare()

    def check(self) -> None:
        for statement in self.statements:
            statement.check()

    def compile(self) -> str:
        return "\n".join(statement.compile() for statement in self.statements)

@__pg.production("block : SYMB_LBRACE statements SYMB_RBRACE")
def __(xs):
    return Block(xs[1])


class If(Statement):
    def __init__(self, condition: Expression, then_body: Block, else_body: Block | If | None) -> None:
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body

    def declare(self) -> None:
        self.condition.scope = self.scope
        self.condition.declare()

        self.then_body.scope = Scope(self.scope)
        self.then_body.declare()

        if self.else_body is not None:
            self.else_body.scope = Scope(self.scope)
            self.else_body.declare()

    def check(self) -> None:
        self.condition.check()
        self.then_body.check()

        if self.else_body is not None:
            self.else_body.check()

@__pg.production("if : KEYW_IF expression block KEYW_ELSE block")
def __(xs):
    return If(xs[1], xs[2], xs[4])

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

    def declare(self) -> None:
        self.scope.declare_var(self.name, self.type)

        if self.value is not None:
            self.value.scope = self.scope
            self.value.declare()

    def check(self) -> None:
        if self.value is None:
            return

        self.value.check()

        if not self.value.get_type().can_be_implicitly_casted_to(self.type):
            raise ValueError(f"Cannot assign {self.value!r} to {self.type!r}")

    def compile(self) -> str:
        if self.value is None:
            return ""

        return self.value.compile_into(self.scope.get_var_address(self.name))


@__pg.production("var : KEYW_VAR OTHR_IDENT SYMB_COLON type SYMB_EQ expression")
def __(xs):
    return Var(xs[1].getstr(), xs[3], xs[5])

@__pg.production("var : KEYW_VAR OTHR_IDENT SYMB_COLON type")
def __(xs):
    return Var(xs[1].getstr(), xs[3])


class Type(Node):
    def can_be_implicitly_casted_to(self, other: Type) -> bool:
        return self == other

    def __eq__(self, other) -> bool:
        return isinstance(other, self.__class__)

class PrimitiveType(Type):
    pass

class VoidType(PrimitiveType):
    pass

class IntegerType(PrimitiveType):
    def __init__(self, value: int | None = None) -> None:
        self.value = value

    def can_be_implicitly_casted_to(self, other: Type) -> bool:
        if self.value is not None:
            if isinstance(other, U8Type) and 0 <= self.value and self.value <= 255:
                return True

            if isinstance(other, I8Type) and -128 <= self.value and self.value <= 127:
                return True

        return super().can_be_implicitly_casted_to(other)

class I8Type(IntegerType):
    pass

class U8Type(IntegerType):
    pass

class CharType(PrimitiveType):
    pass

class BoolType(PrimitiveType):
    pass

class PointerType(PrimitiveType):
    def __init__(self, type: Type) -> None:
        self.type = type

    def __eq__(self, other: Type) -> bool:
        return isinstance(other, self.__class__) and self.type == other.type

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
    def get_type(self) -> Type:
        raise NotImplementedError(self.__class__.__name__)

    def compile_into(self, destination: Destination) -> str:
        raise NotImplementedError(self.__class__.__name__)

__pg.production("expression : literal | call | ident | deref | eqeq") \
    (__first)


class Deref(Expression):
    def __init__(self, expr: Expression) -> None:
        self.expr = expr

    def declare(self) -> None:
        self.expr.scope = self.scope
        self.expr.declare()

    def check(self) -> None:
        if not isinstance(self.expr.get_type(), PointerType):
            raise ValueError(f"Cannot dereference {self.expr!r}")

        self.expr.check()

    def get_type(self) -> Type:
        return self.expr.get_type().type

@__pg.production("deref : SYMB_STAR expression")
def __(xs):
    return Deref(xs[1])


class EqEq(Expression):
    def __init__(self, left: Expression, right: Expression) -> None:
        self.left = left
        self.right = right

    def declare(self) -> None:
        self.left.scope = self.scope
        self.left.declare()

        self.right.scope = self.scope
        self.right.declare()

    def check(self) -> None:
        self.left.check()
        self.right.check()

        if not self.left.get_type().can_be_implicitly_casted_to(self.right.get_type()) and not self.right.get_type().can_be_implicitly_casted_to(self.left.get_type()):
            raise ValueError(f"Cannot compare {self.left!r} to {self.right!r}")

    def get_type(self) -> Type:
        return BoolType()

@__pg.production("eqeq : expression SYMB_EQEQ expression")
def __(xs):
    return EqEq(xs[0], xs[2])


class Ident(Expression):
    def __init__(self, name: str) -> None:
        self.name = name

    def declare(self) -> None:
        pass

    def check(self) -> None:
        pass

    def get_type(self) -> Type:
        return self.scope.get_var_type(self.name)

    def compile_into(self, destination: Destination) -> str:
        if isinstance(destination, RegisterOffsetDestination):
            var_addr = self.scope.get_var_address(self.name)
            if isinstance(var_addr, RegisterOffsetDestination):
                with self.scope.alloc_register() as reg:
                    return f"mld {repr_register(reg)}, {var_addr}, {repr_offset(0)}\n" + destination.load_from_register(reg)
            elif isinstance(var_addr, MemoryDestination):
                with self.scope.alloc_register() as reg_addr:
                    return f"ldi {reg_addr}, {repr_immediate(var_addr.address)}\n" \
                           f"mld {repr_register(reg_addr)}, {repr_register(reg_addr)}, {repr_offset(0)}\n" \
                           + destination.load_from_register(reg_addr)
            else:
                raise NotImplementedError(var_addr)
        else:
            raise NotImplementedError(destination)

@__pg.production("ident : OTHR_IDENT")
def __(xs):
    return Ident(xs[0].getstr())


class Call(Expression):
    def __init__(self, name: str, args: list[Expression]) -> None:
        self.name = name
        self.args = args

    def declare(self) -> None:
        for arg in self.args:
            arg.scope = self.scope
            arg.declare()

    def check(self) -> None:
        for arg in self.args:
            arg.check()

        func = self.scope.get_func(self.name)

        if len(func[0]) != len(self.args):
            raise ValueError(f"Function {self.name!r} expects {len(func[0])} arguments, got {len(self.args)}")

        for arg, param in zip(self.args, func[0]):
            if not arg.get_type().can_be_implicitly_casted_to(param):
                raise ValueError(f"Cannot pass {arg!r} to {param!r}")

    def compile(self) -> str:
        if self.name == "write_port":
            if not isinstance(self.args[0], IntLiteral):
                raise ValueError("Port argument must be a literal")

            lines = []

            with self.scope.alloc_register() as reg_port:
                lines.append(self.args[0].compile_into(reg_port))
                lines.append(f"pst {reg_port}, {repr_immediate(self.args[1].value)}")

            # TODO: Move the return value somewhere

            return "\n".join(lines)
        elif self.name == "read_port":
            if not isinstance(self.args[0], IntLiteral):
                raise ValueError("Port argument must be a literal")

            lines = []

            with self.scope.alloc_register() as reg_port:
                lines.append(self.args[0].compile_into(reg_port))
                lines.append(f"pld {reg_port}, {repr_immediate(self.args[1].value)}")

            # TODO: Move the return value somewhere

            return "\n".join(lines)

        lines = []

        with self.scope.alloc_register() as old_base:
            lines.append(f"mov {repr_register(old_base)}, {repr_register(BASE_POINTER_REG)}")
            lines.append(f"mov {repr_register(BASE_POINTER_REG)}, {repr_register(STACK_POINTER_REG)}")
            lines.append(f"adi {repr_register(STACK_POINTER_REG)}, {repr_immediate(-(len(self.args) + 1))}")
            lines.append(f"cmp {repr_register(STACK_POINTER_REG)}, {repr_immediate(STACK_END)}")
            lines.append(f"jmp less {repr_batc_label('stack_overflow')}")
            lines.append(f"mst {repr_register(STACK_POINTER_REG)}, {repr_offset(len(self.args))}, {repr_register(old_base)}")
            for i, arg in enumerate(self.args):
                lines.append(arg.compile_into(RegisterOffsetDestination(STACK_POINTER_REG, i)))
            lines.append(f"cal {repr_user_label(self.name)}")
            lines.append(f"mld {repr_register(BASE_POINTER_REG)}, {repr_register(STACK_POINTER_REG)}, {repr_offset(len(self.args))}")
            lines.append(f"adi {repr_register(STACK_POINTER_REG)}, {repr_immediate(len(self.args) + 1)}")

        # TODO: Move the return value somewhere

        return "\n".join(lines)

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

    def declare(self) -> None:
        pass

    def check(self) -> None:
        if self.value & 0xFF != self.value:
            self.warn("Integer literal out of range, will be truncated to 8 bits")
            self.value &= 0xFF

    def compile_into(self, destination: Destination) -> str:
        if isinstance(destination, RegisterOffsetDestination):
            with self.scope.alloc_register() as reg:
                return f"ldi {reg}, {repr_immediate(self.value)}\n" + destination.load_from_register(reg)
        elif isinstance(destination, MemoryDestination):
            with self.scope.alloc_register() as reg_value:
                with self.scope.alloc_register() as reg_addr:
                    return f"ldi {reg_value}, {repr_immediate(self.value)}\n" \
                           f"ldi {reg_addr}, {repr_immediate(destination.address)}\n" \
                           f"mst {reg_addr}, {repr_offset(0)}, {repr_register(reg_value)}"
        elif isinstance(destination, RegisterDestination):
            return f"ldi {repr_register(destination.register)}, {repr_immediate(self.value)}"
        else:
            raise NotImplementedError(destination)

    def get_type(self) -> Type:
        if self.value < 0:
            return I8Type(self.value)

        return U8Type(self.value)

class StringLiteral(Literal):
    def __init__(self, value: str) -> None:
        self.value = value

    def check(self) -> None:
        pass

    def get_type(self) -> Type:
        return PointerType(CharType())

class CharLiteral(Literal):
    def __init__(self, value: str) -> None:
        if len(value) != 1:
            raise ValueError("CharLiteral value must be exactly one character")

        self.value = value

    def declare(self) -> None:
        pass

    def check(self) -> None:
        pass

    def get_type(self) -> Type:
        return CharType()

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
