"""Tokenizer for .ezsf files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    IDENT = auto()
    NUMBER = auto()
    STRING = auto()
    PERCENT = auto()
    COMMA = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    PIPE = auto()
    EQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()
    AT = auto()
    NEWLINE = auto()
    EOF = auto()
    COMMENT = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    col: int


KEYWORDS = {
    "version",
    "dimension",
    "biome",
    "structure",
    "stronghold",
    "spawn",
    "bastion",
    "distance",
    "terrain",
    "height",
    "loot",
    "mob",
    "threads",
    "max_results",
    "seed_range",
    "random",
    "sequential",
    "at",
    "within",
    "of",
    "viable",
    "not",
    "contains",
    "between",
    "nearest",
    "under",
    "full",
    "ring",
    "giant",
    "cold",
    "flat",
    "mountainous",
    "oceanic",
    "region",
    "to",
    "from",
    "start",
    "end",
    "variant",
    "overworld",
    "nether",
    "end",
    "and",
    "or",
    "count",
    "ruined_portal",
    "top_missing",
    "frame_missing",
    "underground",
    "airpocket",
    "template",
    "normal",
    "chest",
    "item",
    "min",
    "count",
    "abandoned",
}


class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.col = 1

    def _peek(self, n: int = 0) -> str:
        i = self.pos + n
        return self.text[i] if i < len(self.text) else ""

    def _advance(self) -> str:
        ch = self._peek()
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _skip_ws(self) -> None:
        while self._peek() and self._peek() in " \t\r":
            self._advance()

    def next_token(self) -> Token:
        self._skip_ws()
        start_line, start_col = self.line, self.col
        ch = self._peek()

        if not ch:
            return Token(TokenType.EOF, "", start_line, start_col)

        if ch == "#":
            while self._peek() and self._peek() != "\n":
                self._advance()
            return Token(TokenType.COMMENT, "", start_line, start_col)

        if ch == "\n":
            self._advance()
            return Token(TokenType.NEWLINE, "\n", start_line, start_col)

        two = ch + self._peek(1)
        if two in ("<=", ">=", "!=", "=="):
            self._advance()
            self._advance()
            mapping = {
                "<=": TokenType.LTE,
                ">=": TokenType.GTE,
                "!=": TokenType.NEQ,
                "==": TokenType.EQ,
            }
            return Token(mapping[two], two, start_line, start_col)

        singles = {
            ",": TokenType.COMMA,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            "|": TokenType.PIPE,
            "<": TokenType.LT,
            ">": TokenType.GT,
            "@": TokenType.AT,
            "%": TokenType.PERCENT,
        }
        if ch in singles:
            self._advance()
            if ch == "=":
                return Token(TokenType.EQ, "=", start_line, start_col)
            return Token(singles[ch], ch, start_line, start_col)

        if ch in "\"'":
            quote = self._advance()
            buf = []
            while self._peek() and self._peek() != quote:
                if self._peek() == "\\":
                    self._advance()
                    buf.append(self._advance())
                else:
                    buf.append(self._advance())
            if self._peek() == quote:
                self._advance()
            return Token(TokenType.STRING, "".join(buf), start_line, start_col)

        if ch.isdigit() or (ch == "-" and self._peek(1).isdigit()):
            buf = []
            if ch == "-":
                buf.append(self._advance())
            while self._peek().isdigit():
                buf.append(self._advance())
            while self._peek() == "." and self._peek(1).isdigit():
                buf.append(self._advance())
                while self._peek().isdigit():
                    buf.append(self._advance())
            return Token(TokenType.NUMBER, "".join(buf), start_line, start_col)

        if ch.isalpha() or ch == "_":
            buf = []
            while self._peek() and (self._peek().isalnum() or self._peek() in "._-"):
                buf.append(self._advance())
            return Token(TokenType.IDENT, "".join(buf), start_line, start_col)

        self._advance()
        return Token(TokenType.IDENT, ch, start_line, start_col)

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while True:
            tok = self.next_token()
            if tok.type == TokenType.COMMENT:
                continue
            tokens.append(tok)
            if tok.type == TokenType.EOF:
                break
        return tokens
