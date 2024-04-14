from rply import LexerGenerator, Token
from enum import StrEnum


class TokenType(StrEnum):
    # keywords
    KEYW_FUNC = r"func"
    KEYW_VAR = r"var"
    KEYW_IF = r"if"
    KEYW_ELSE = r"else"
    KEYW_WHILE = r"while"
    KEYW_RETURN = r"return"

    # types
    TYPE_VOID = r"void"
    TYPE_I8 = r"i8"
    TYPE_U8 = r"u8"
    TYPE_CHAR = r"char"
    TYPE_BOOL = r"bool"

    # symbols
    SYMB_ARROW = r"->"
    SYMB_EQEQ = r"=="
    SYMB_PLUS = r"\+"
    SYMB_MINUS = r"-"
    SYMB_EQ = r"="
    SYMB_COLON = r":"
    SYMB_STAR = r"\*"
    SYMB_LPAREN = r"\("
    SYMB_RPAREN = r"\)"
    SYMB_LBRACE = r"{"
    SYMB_RBRACE = r"}"
    SYMB_COMMA = r","

    # literals
    LITR_INT = r"\d+"
    LITR_STRING = r"\".*\""
    LITR_CHAR = r"'.*'"
    LITR_BOOL = r"true|false"

    # other
    OTHR_IDENT = r"[a-zA-Z_][a-zA-Z0-9_]*"
    OTHR_NEWLINE = r"\n"
    OTHR_COMMENT = r"#.*"


__lg = LexerGenerator()

for token in TokenType:
    __lg.add(token._name_, token._value_)

# ignore all whitespace but newlines
__lg.ignore(r"[ \t\f\v]+")

__lexer = __lg.build()

def __remove_consecutive_newlines(tokens: list[Token]) -> list[Token]:
    new_tokens = []

    for i, token in enumerate(tokens):
        if i + 1 >= len(tokens):
            new_tokens.append(token)
            continue

        if token.name == TokenType.OTHR_NEWLINE._name_ and tokens[i + 1].name == TokenType.OTHR_NEWLINE._name_:
            continue

        new_tokens.append(token)

    return new_tokens

def __remove_comments(tokens: list[Token]) -> list[Token]:
    return [token for token
            in tokens
            if token.name != TokenType.OTHR_COMMENT._name_]

def lex(source: str) -> list[Token]:
    source = source.strip()
    if not source.endswith("\n"):
        source += "\n"

    tokens = list(__lexer.lex(source))

    tokens = __remove_comments(tokens)
    tokens = __remove_consecutive_newlines(tokens)

    return tokens
