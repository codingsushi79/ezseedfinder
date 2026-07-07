"""AST nodes for .ezsf criteria language."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    version: str | None = None
    threads: int | None = None
    max_results: int | None = None
    seed_start: int | None = None
    seed_end: int | None = None
    random_search: bool = True
    statements: list[Any] = field(default_factory=list)


@dataclass
class DimensionBlock:
    dimension: str
    statements: list[Any] = field(default_factory=list)


@dataclass
class BiomeAt:
    dimension: str
    x: int
    y: int
    z: int
    biomes: list[str]
    negate: bool = False


@dataclass
class BiomeRegion:
    dimension: str
    x1: int
    z1: int
    x2: int
    z2: int
    y: int
    biome: str
    op: str  # contains, ==, >=, <=
    percent: float | None = None


@dataclass
class StructureRule:
    dimension: str
    structure: str
    ref: str
    ref_pos: tuple[int, int] | None
    max_dist: int
    viable: bool = True
    count_min: int = 1


@dataclass
class StructureBetween:
    dimension: str
    structure_a: str
    structure_b: str
    ref: str
    ref_pos: tuple[int, int] | None
    max_dist: int
    viable: bool = True


@dataclass
class StrongholdRule:
    nearest_max_dist: int | None = None
    ref: str = "spawn"
    ref_pos: tuple[int, int] | None = None
    count: int = 128
    under_player: bool = False
    full: bool = False
    ring: int | None = None


@dataclass
class SpawnRule:
    ref: str = "origin"
    ref_pos: tuple[int, int] | None = None
    max_dist: int | None = None
    biomes: list[str] = field(default_factory=list)


@dataclass
class BastionRule:
    variant: str
    ref: str
    ref_pos: tuple[int, int] | None
    max_dist: int
    viable: bool = True


@dataclass
class DistanceRule:
    kind: str  # structures | points
    a: str
    b: str
    dimension: str
    op: str
    value: float
    ref: str | None = None
    ref_pos: tuple[int, int] | None = None
    max_search: int = 2000


@dataclass
class TerrainRule:
    dimension: str
    x: int
    z: int
    radius: int
    predicate: str  # flat, mountainous, oceanic
    negate: bool = False


@dataclass
class HeightRule:
    dimension: str
    x: int
    z: int
    op: str
    value: int


@dataclass
class RuinedPortalRule:
    dimension: str
    ref: str
    ref_pos: tuple[int, int] | None
    max_dist: int
    giant: bool | None = None
    cold: bool | None = None
    underground: bool | None = None
    airpocket: bool | None = None
    template: int | None = None
    top_missing: int | None = None
    frame_missing: int | None = None
    chest_items: list[tuple[str, int]] = field(default_factory=list)
    viable: bool = True


@dataclass
class StructureVariantRule:
    """Attach variant constraints to a nearby structure."""
    dimension: str
    structure: str
    ref: str
    ref_pos: tuple[int, int] | None
    max_dist: int
    bastion_variant: str | None = None
    village_abandoned: bool | None = None
    giant: bool | None = None
    underground: bool | None = None
    airpocket: bool | None = None
    template: int | None = None
    viable: bool = True


@dataclass
class LootRule:
    structure: str
    item: str
    min_count: int = 1
    dimension: str = "overworld"
    ref: str = "origin"
    ref_pos: tuple[int, int] | None = None
    max_dist: int = 5000
    loot_table: str | None = None


@dataclass
class MobRule:
    """Mob spawn biome rules — uses biome viability as proxy."""
    mob: str
    dimension: str
    ref: str
    ref_pos: tuple[int, int] | None
    max_dist: int
    biomes: list[str] = field(default_factory=list)


@dataclass
class Comment:
    text: str
