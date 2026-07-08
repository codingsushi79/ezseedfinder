"""Estimate chest block coordinates for structure loot RNG."""

from __future__ import annotations

from cubiomespi import Dimension

from .cubiomes_backend import WorldContext, structure_id
from .loot_tables import STRUCTURE_DEFAULT_LOOT_TABLE
from .variants import get_structure_variant

# Fallback Y when cubiomes variant height is unavailable
_DEFAULT_Y: dict[str, int] = {
    "buried_treasure": 8,
    "treasure": 8,
    "shipwreck": 62,
    "shipwreck_treasure": 62,
    "desert_pyramid": 66,
    "jungle_temple": 66,
    "jungle_pyramid": 66,
    "bastion_treasure": 80,
    "bastion": 80,
    "ancient_city": -41,
    "trail_ruins": 64,
    "trail_ruin": 64,
    "ruined_portal": 64,
    "ruined_portal_n": 48,
}


def default_loot_table(struct_name: str) -> str | None:
    key = struct_name.strip().lower().replace("-", "_")
    return STRUCTURE_DEFAULT_LOOT_TABLE.get(key)


def loot_chest_coords(
    ctx: WorldContext,
    mc_version: int,
    dimension: int,
    struct_name: str,
    x: int,
    z: int,
) -> tuple[int, int, int]:
    """Return block coords (x, y, z) used for chest loot seeding."""
    key = struct_name.strip().lower().replace("-", "_")
    biome = ctx.biome_at(dimension, x, 64, z).value
    try:
        struct = structure_id(key)
    except ValueError:
        struct = structure_id(struct_name)
    sv = get_structure_variant(struct, mc_version, ctx.seed, x, z, biome)

    cx, cz = x, z
    if sv is not None:
        if sv.x or sv.z:
            cx = x + int(sv.x)
            cz = z + int(sv.z)
        if sv.y != 0:
            return cx, int(sv.y), cz

    if dimension == Dimension.DIM_NETHER:
        return cx, _DEFAULT_Y.get(key, 48), cz
    if dimension == Dimension.DIM_END:
        return cx, ctx.end_surface_y(cx, cz), cz
    return cx, _DEFAULT_Y.get(key, 64), cz
