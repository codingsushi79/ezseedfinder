"""Recursive descent parser for .ezsf criteria files."""

from __future__ import annotations

from .ast import (
    BastionRule,
    BiomeAt,
    BiomeRegion,
    DimensionBlock,
    DistanceRule,
    Document,
    HeightRule,
    LootRule,
    MobRule,
    RuinedPortalRule,
    SpawnRule,
    StrongholdRule,
    StructureBetween,
    StructureRule,
    TerrainRule,
)
from .lexer import Lexer, Token, TokenType


class ParseError(Exception):
    def __init__(self, message: str, token: Token | None = None):
        if token:
            super().__init__(f"{message} at line {token.line}, col {token.col}")
        else:
            super().__init__(message)
        self.token = token


class Parser:
    def __init__(self, text: str):
        self.tokens = Lexer(text).tokenize()
        self.pos = 0

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _match(self, *types: TokenType) -> Token | None:
        if self._peek().type in types:
            return self._advance()
        return None

    def _expect(self, ttype: TokenType, msg: str) -> Token:
        tok = self._peek()
        if tok.type != ttype:
            raise ParseError(msg, tok)
        return self._advance()

    def _skip_newlines(self) -> None:
        while self._peek().type == TokenType.NEWLINE:
            self._advance()

    def _parse_number(self) -> int:
        tok = self._expect(TokenType.NUMBER, "Expected number")
        return int(tok.value)

    def _parse_ident(self) -> str:
        tok = self._expect(TokenType.IDENT, "Expected identifier")
        return tok.value

    def _parse_biome_list(self) -> list[str]:
        biomes = [self._parse_ident()]
        while self._match(TokenType.PIPE):
            biomes.append(self._parse_ident())
        return biomes

    def _parse_point_ref(self) -> tuple[str, tuple[int, int] | None]:
        if self._peek().type == TokenType.NUMBER:
            x = self._parse_number()
            self._expect(TokenType.COMMA, "Expected comma in coordinate")
            z = self._parse_number()
            return ("custom", (x, z))
        ref = self._parse_ident().lower()
        if ref == "0,0":
            return ("origin", (0, 0))
        return (ref, None)

    def parse(self) -> Document:
        doc = Document()
        self._skip_newlines()
        while self._peek().type != TokenType.EOF:
            self._skip_newlines()
            if self._peek().type == TokenType.EOF:
                break
            stmt = self._parse_toplevel()
            if stmt is not None:
                if isinstance(stmt, tuple) and stmt[0] == "meta":
                    key, val = stmt[1], stmt[2]
                    setattr(doc, key, val)
                else:
                    doc.statements.append(stmt)
            self._skip_newlines()
        return doc

    def _parse_toplevel(self):
        ident = self._peek()
        if ident.type != TokenType.IDENT:
            raise ParseError("Expected statement", ident)
        kw = ident.value.lower()

        if kw == "version":
            self._advance()
            tok = self._peek()
            if tok.type == TokenType.NUMBER:
                self._advance()
                ver = tok.value
            else:
                ver = self._parse_ident()
            return ("meta", "version", ver)

        if kw == "threads":
            self._advance()
            return ("meta", "threads", self._parse_number())

        if kw == "max_results":
            self._advance()
            return ("meta", "max_results", self._parse_number())

        if kw == "seed_range":
            self._advance()
            self._expect_ident("start")
            start = self._parse_number()
            self._expect_ident("end")
            end = self._parse_number()
            doc_meta = [("meta", "seed_start", start), ("meta", "seed_end", end)]
            return doc_meta

        if kw == "random":
            self._advance()
            return ("meta", "random_search", True)

        if kw == "sequential":
            self._advance()
            return ("meta", "random_search", False)

        if kw == "dimension":
            return self._parse_dimension_block()

        if kw == "stronghold":
            return self._parse_stronghold()

        if kw == "spawn":
            return self._parse_spawn()

        if kw == "distance":
            return self._parse_distance()

        if kw == "loot":
            return self._parse_loot()

        if kw == "ruined_portal":
            return self._parse_ruined_portal_stmt("overworld")

        if kw == "mob":
            return self._parse_mob()

        raise ParseError(f"Unknown top-level keyword: {kw}", ident)

    def _expect_ident(self, value: str) -> None:
        tok = self._expect(TokenType.IDENT, f"Expected '{value}'")
        if tok.value.lower() != value:
            raise ParseError(f"Expected '{value}', got '{tok.value}'", tok)

    def _parse_dimension_block(self) -> DimensionBlock:
        self._expect_ident("dimension")
        dim = self._parse_ident().lower()
        self._expect(TokenType.LBRACE, "Expected '{' after dimension")
        block = DimensionBlock(dimension=dim)
        self._skip_newlines()
        while self._peek().type != TokenType.RBRACE:
            if self._peek().type == TokenType.EOF:
                raise ParseError("Unclosed dimension block")
            block.statements.append(self._parse_dimension_stmt(dim))
            self._skip_newlines()
        self._advance()
        return block

    def _parse_dimension_stmt(self, dim: str):
        kw = self._peek().value.lower()
        if kw == "biome":
            return self._parse_biome_stmt(dim)
        if kw == "structure":
            return self._parse_structure_stmt(dim)
        if kw == "bastion":
            return self._parse_bastion_stmt(dim)
        if kw == "terrain":
            return self._parse_terrain_stmt(dim)
        if kw == "height":
            return self._parse_height_stmt(dim)
        if kw == "ruined_portal":
            return self._parse_ruined_portal_stmt(dim)
        raise ParseError(f"Unknown statement in dimension block: {kw}")

    def _parse_biome_stmt(self, dim: str):
        self._expect_ident("biome")
        negate = False
        if self._peek().value.lower() == "not":
            self._advance()
            negate = True

        if self._peek().value.lower() == "region":
            self._advance()
            x1 = self._parse_number()
            self._expect(TokenType.COMMA, "Expected comma")
            z1 = self._parse_number()
            self._expect_ident("to")
            x2 = self._parse_number()
            self._expect(TokenType.COMMA, "Expected comma")
            z2 = self._parse_number()
            y = 64
            if self._peek().value.lower() == "y":
                self._advance()
                y = self._parse_number()
            op_tok = self._advance()
            if op_tok.value.lower() == "contains":
                op = "contains"
            elif op_tok.type in (TokenType.GTE, TokenType.LTE, TokenType.EQ):
                op = {TokenType.GTE: ">=", TokenType.LTE: "<=", TokenType.EQ: "=="}.get(
                    op_tok.type, op_tok.value
                )
            else:
                op = op_tok.value
            biome = self._parse_ident()
            percent = None
            if self._peek().type in (TokenType.GTE, TokenType.LTE):
                op = ">=" if self._peek().type == TokenType.GTE else "<="
                self._advance()
                percent = float(self._parse_number())
                self._match(TokenType.PERCENT)
            return BiomeRegion(dim, x1, z1, x2, z2, y, biome, op, percent)

        self._expect_ident("at")
        if self._peek().value.lower() == "spawn":
            self._advance()
            y = 64
            if self._peek().type == TokenType.NUMBER:
                y = self._parse_number()
            if self._peek().type in (TokenType.EQ,):
                self._advance()
            biomes = self._parse_biome_list()
            return BiomeAt(dim, -1, y, -1, biomes, negate)

        x = self._parse_number()
        self._expect(TokenType.COMMA, "Expected comma")
        y = self._parse_number()
        self._expect(TokenType.COMMA, "Expected comma")
        z = self._parse_number()
        biomes = self._parse_biome_list_after_eq()
        return BiomeAt(dim, x, y, z, biomes, negate)

    def _parse_biome_list_after_eq(self) -> list[str]:
        if self._peek().type in (TokenType.EQ,):
            self._advance()
        elif self._peek().value == "==":
            self._advance()
        return self._parse_biome_list()

    def _parse_structure_stmt(self, dim: str) -> StructureRule:
        self._expect_ident("structure")
        if self._peek().value.lower() == "between":
            return self._parse_structure_between(dim)
        structure = self._parse_ident().lower()
        self._expect_ident("within")
        max_dist = self._parse_number()
        self._expect_ident("of")
        ref, ref_pos = self._parse_point_ref()
        viable = True
        count_min = 1
        village_abandoned: bool | None = None
        while self._peek().type == TokenType.IDENT:
            mod = self._peek().value.lower()
            if mod == "viable":
                self._advance()
                viable = True
            elif mod == "not" and self._peek_ahead_ident("viable"):
                self._advance()
                self._expect_ident("viable")
                viable = False
            elif mod == "count":
                self._advance()
                self._expect_ident("min")
                count_min = self._parse_number()
            elif mod == "abandoned":
                self._advance()
                village_abandoned = self._parse_bool_value()
            else:
                break
        return StructureRule(
            dim, structure, ref, ref_pos, max_dist, viable, count_min, village_abandoned
        )

    def _peek_ahead_ident(self, value: str) -> bool:
        return self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].value.lower() == value

    def _parse_structure_between(self, dim: str) -> StructureBetween:
        self._expect_ident("between")
        a = self._parse_ident().lower()
        self._expect_ident("and")
        b = self._parse_ident().lower()
        self._expect_ident("within")
        max_dist = self._parse_number()
        self._expect_ident("of")
        ref, ref_pos = self._parse_point_ref()
        viable = self._peek().value.lower() == "viable"
        if viable:
            self._advance()
        return StructureBetween(dim, a, b, ref, ref_pos, max_dist, viable)

    def _parse_bastion_stmt(self, dim: str) -> BastionRule:
        self._expect_ident("bastion")
        self._expect_ident("variant")
        variant = self._parse_ident().lower()
        self._expect_ident("within")
        max_dist = self._parse_number()
        self._expect_ident("of")
        ref, ref_pos = self._parse_point_ref()
        viable = self._peek().value.lower() == "viable"
        if viable:
            self._advance()
        return BastionRule(variant, ref, ref_pos, max_dist, viable)

    def _parse_terrain_stmt(self, dim: str) -> TerrainRule:
        self._expect_ident("terrain")
        self._expect_ident("at")
        x = self._parse_number()
        self._expect(TokenType.COMMA, "Expected comma")
        z = self._parse_number()
        predicate = self._parse_ident().lower()
        negate = False
        if self._peek().value.lower() == "not":
            self._advance()
            negate = True
        radius = 64
        if self._peek().value.lower() == "radius":
            self._advance()
            radius = self._parse_number()
        return TerrainRule(dim, x, z, radius, predicate, negate)

    def _parse_height_stmt(self, dim: str) -> HeightRule:
        self._expect_ident("height")
        self._expect_ident("at")
        x = self._parse_number()
        self._expect(TokenType.COMMA, "Expected comma")
        z = self._parse_number()
        op_tok = self._advance()
        op = {TokenType.LT: "<", TokenType.GT: ">", TokenType.LTE: "<=", TokenType.GTE: ">="}.get(
            op_tok.type, op_tok.value
        )
        value = self._parse_number()
        return HeightRule(dim, x, z, op, value)

    def _parse_ruined_portal_stmt(self, dim: str) -> RuinedPortalRule:
        self._expect_ident("ruined_portal")
        rule = RuinedPortalRule(dim, "origin", None, 0)
        if self._peek().value.lower() in ("giant", "cold", "normal"):
            mod = self._advance().value.lower()
            if mod == "giant":
                rule.giant = True
            elif mod == "cold":
                rule.cold = True
            elif mod == "normal":
                rule.giant = False
        if self._peek().value.lower() == "within":
            self._advance()
            rule.max_dist = self._parse_number()
            self._expect_ident("of")
            rule.ref, rule.ref_pos = self._parse_point_ref()
        self._parse_portal_modifiers(rule)
        return rule

    def _parse_portal_modifiers(self, rule: RuinedPortalRule) -> None:
        while self._peek().type == TokenType.IDENT:
            kw = self._peek().value.lower()
            if kw == "viable":
                self._advance()
                rule.viable = True
            elif kw == "not" and self._peek_ahead_ident("viable"):
                self._advance()
                self._expect_ident("viable")
                rule.viable = False
            elif kw == "giant":
                self._advance()
                rule.giant = self._parse_bool_value()
            elif kw == "underground":
                self._advance()
                rule.underground = self._parse_bool_value()
            elif kw == "airpocket":
                self._advance()
                rule.airpocket = self._parse_bool_value()
            elif kw == "template":
                self._advance()
                rule.template = self._parse_number()
            elif kw == "top_missing":
                self._advance()
                rule.top_missing = self._parse_number()
            elif kw == "frame_missing":
                self._advance()
                rule.frame_missing = self._parse_number()
            elif kw == "chest":
                self._advance()
                if self._peek().value.lower() == "item":
                    self._advance()
                item = self._parse_ident().lower()
                count = 1
                if self._peek().value.lower() in ("min", "count"):
                    self._advance()
                    count = self._parse_number()
                rule.chest_items.append((item, count))
            else:
                break

    def _parse_bool_value(self) -> bool:
        if self._peek().type in (TokenType.IDENT,):
            val = self._advance().value.lower()
            if val in ("true", "yes", "on", "1"):
                return True
            if val in ("false", "no", "off", "0"):
                return False
        return True

    def _parse_stronghold(self) -> StrongholdRule:
        self._expect_ident("stronghold")
        rule = StrongholdRule()
        while self._peek().type == TokenType.IDENT:
            kw = self._peek().value.lower()
            if kw == "nearest":
                self._advance()
                self._expect_ident("within")
                rule.nearest_max_dist = self._parse_number()
                self._expect_ident("of")
                rule.ref, rule.ref_pos = self._parse_point_ref()
            elif kw == "under":
                self._advance()
                self._expect_ident("spawn")
                rule.under_player = True
            elif kw == "full":
                self._advance()
                rule.full = True
            elif kw == "ring":
                self._advance()
                rule.ring = self._parse_number()
            elif kw == "max_angle":
                self._advance()
                rule.max_angle_deg = float(self._parse_number())
            elif kw == "count":
                self._advance()
                rule.count = self._parse_number()
            else:
                break
        return rule

    def _parse_spawn(self) -> SpawnRule:
        self._expect_ident("spawn")
        rule = SpawnRule()
        if self._peek().value.lower() == "within":
            self._advance()
            rule.max_dist = self._parse_number()
            self._expect_ident("of")
            rule.ref, rule.ref_pos = self._parse_point_ref()
        if self._peek().value.lower() == "biome":
            self._advance()
            rule.biomes = self._parse_biome_list()
        return rule

    def _parse_distance(self) -> DistanceRule:
        self._expect_ident("distance")
        a = self._parse_ident().lower()
        b = ""
        kind = "structures"
        if self._peek().type in (TokenType.LTE, TokenType.GTE, TokenType.LT, TokenType.GT, TokenType.EQ):
            kind = "point"
        elif self._peek().value.lower() == "and":
            self._advance()
            b = self._parse_ident().lower()
            kind = "structures"
        elif self._peek().type == TokenType.IDENT:
            b = self._parse_ident().lower()
            kind = "structures"
        op_tok = self._advance()
        op = {TokenType.LTE: "<=", TokenType.GTE: ">=", TokenType.LT: "<", TokenType.GT: ">"}.get(
            op_tok.type, op_tok.value
        )
        value = float(self._parse_number())
        dimension = "overworld"
        ref = None
        ref_pos = None
        max_search = 2000
        if self._peek().value.lower() == "in":
            self._advance()
            dimension = self._parse_ident().lower()
        if self._peek().value.lower() == "from":
            self._advance()
            ref, ref_pos = self._parse_point_ref()
        if self._peek().value.lower() == "search":
            self._advance()
            max_search = self._parse_number()
        return DistanceRule(kind, a, b, dimension, op, value, ref, ref_pos, max_search)

    def _parse_loot(self) -> LootRule:
        self._expect_ident("loot")
        if self._peek().value.lower() == "at":
            self._advance()
        structure = self._parse_ident().lower()
        self._expect_ident("item")
        item = self._parse_ident().lower()
        min_count = 1
        dimension = "overworld"
        ref = "origin"
        ref_pos = None
        max_dist = 5000
        loot_table = None
        if self._peek().value.lower() in ("min", "count"):
            self._advance()
            min_count = self._parse_number()
        if self._peek().value.lower() == "table":
            self._advance()
            loot_table = self._parse_ident().lower()
        if self._peek().value.lower() == "within":
            self._advance()
            max_dist = self._parse_number()
            self._expect_ident("of")
            ref, ref_pos = self._parse_point_ref()
        if self._peek().value.lower() == "in":
            self._advance()
            dimension = self._parse_ident().lower()
        return LootRule(structure, item, min_count, dimension, ref, ref_pos, max_dist, loot_table)

    def _parse_mob(self) -> MobRule:
        self._expect_ident("mob")
        mob = self._parse_ident().lower()
        self._expect_ident("within")
        max_dist = self._parse_number()
        self._expect_ident("of")
        ref, ref_pos = self._parse_point_ref()
        dimension = "overworld"
        biomes: list[str] = []
        if self._peek().value.lower() == "in":
            self._advance()
            dimension = self._parse_ident().lower()
        if self._peek().value.lower() == "biome":
            self._advance()
            biomes = self._parse_biome_list()
        return MobRule(mob, dimension, ref, ref_pos, max_dist, biomes)


def parse_ezsf(text: str) -> Document:
    parser = Parser(text)
    doc = parser.parse()
    # Handle seed_range returning list
    flat_stmts = []
    for stmt in doc.statements:
        if isinstance(stmt, list):
            for item in stmt:
                if isinstance(item, tuple) and item[0] == "meta":
                    setattr(doc, item[1], item[2])
        else:
            flat_stmts.append(stmt)
    doc.statements = flat_stmts
    return doc


def document_to_config(doc: Document) -> dict:
    """Convert parsed document metadata to SearchConfig fields."""
    return {
        "version": doc.version,
        "threads": doc.threads,
        "max_results": doc.max_results,
        "seed_start": doc.seed_start,
        "seed_end": doc.seed_end,
        "random_search": doc.random_search,
        "criteria_ast": doc,
    }
