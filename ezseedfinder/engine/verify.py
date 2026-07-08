"""Seed verification helpers — per-rule pass/fail breakdown."""

from __future__ import annotations

from typing import Any

from ..ezsf.ast import (
    BastionRule,
    BiomeAt,
    BiomeRegion,
    DimensionBlock,
    DistanceRule,
    HeightRule,
    LootRule,
    MobRule,
    RuinedPortalRule,
    SpawnRule,
    StrongholdRule,
    StructureBetween,
    StructureRule,
    StructureVariantRule,
    TerrainRule,
)


def describe_statement(stmt: Any) -> str:
    if isinstance(stmt, DimensionBlock):
        return f"dimension {stmt.dimension}"
    if isinstance(stmt, StructureRule):
        return f"structure {stmt.structure} within {stmt.max_dist}"
    if isinstance(stmt, StructureBetween):
        return f"between {stmt.structure_a} and {stmt.structure_b}"
    if isinstance(stmt, StrongholdRule):
        parts = ["stronghold"]
        if stmt.nearest_max_dist is not None:
            parts.append(f"nearest<={stmt.nearest_max_dist}")
        if stmt.under_player:
            parts.append("under_spawn")
        if stmt.full:
            parts.append("full")
        if stmt.ring is not None:
            parts.append(f"ring={stmt.ring}")
        if stmt.max_angle_deg is not None:
            parts.append(f"max_angle={stmt.max_angle_deg}")
        return " ".join(parts)
    if isinstance(stmt, RuinedPortalRule):
        return f"ruined_portal within {stmt.max_dist}"
    if isinstance(stmt, BastionRule):
        return f"bastion {stmt.variant} within {stmt.max_dist}"
    if isinstance(stmt, LootRule):
        return f"loot {stmt.item} at {stmt.structure}"
    if isinstance(stmt, MobRule):
        return f"mob {stmt.mob} within {stmt.max_dist}"
    if isinstance(stmt, SpawnRule):
        return "spawn rule"
    if isinstance(stmt, BiomeAt):
        return f"biome at {stmt.x},{stmt.z}"
    if isinstance(stmt, BiomeRegion):
        return f"biome region {stmt.biome}"
    if isinstance(stmt, TerrainRule):
        return f"terrain {stmt.predicate}"
    if isinstance(stmt, HeightRule):
        return f"height {stmt.op} {stmt.value}"
    if isinstance(stmt, DistanceRule):
        return f"distance {stmt.a} {stmt.b}"
    if isinstance(stmt, StructureVariantRule):
        return f"variant {stmt.structure}"
    return type(stmt).__name__
