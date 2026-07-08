"""Thin wrapper around cubiomespi with naming helpers."""

from __future__ import annotations

import math
from typing import Any

from cubiomespi import BiomeID, Dimension, Generator, MCVersion, Structure
from cubiomespi.util import distance_between_points

VERSION_MAP: dict[str, MCVersion] = {
    "1.0": MCVersion.MC_1_0_0,
    "1.0.0": MCVersion.MC_1_0_0,
    "1.1": MCVersion.MC_1_1_0,
    "1.1.0": MCVersion.MC_1_1_0,
    "1.2.5": MCVersion.MC_1_2_5,
    "1.3.2": MCVersion.MC_1_3_2,
    "1.4.7": MCVersion.MC_1_4_7,
    "1.5.2": MCVersion.MC_1_5_2,
    "1.6.4": MCVersion.MC_1_6_4,
    "1.7.10": MCVersion.MC_1_7_10,
    "1.8.9": MCVersion.MC_1_8_9,
    "1.9.4": MCVersion.MC_1_9_4,
    "1.10.2": MCVersion.MC_1_10_2,
    "1.11.2": MCVersion.MC_1_11_2,
    "1.12.2": MCVersion.MC_1_12_2,
    "1.13.2": MCVersion.MC_1_13_2,
    "1.14.4": MCVersion.MC_1_14_4,
    "1.15.2": MCVersion.MC_1_15_2,
    "1.16": MCVersion.MC_1_16_1,
    "1.16.1": MCVersion.MC_1_16_1,
    "1.16.5": MCVersion.MC_1_16_5,
    "1.17.1": MCVersion.MC_1_17_1,
    "1.18.2": MCVersion.MC_1_18_2,
    "1.19": MCVersion.MC_1_19,
    "1.19.2": MCVersion.MC_1_19_2,
    "1.20": MCVersion.MC_1_20,
    "1.21": MCVersion.MC_1_21,
    "26.1": getattr(MCVersion, "MC_26_1", MCVersion.MC_1_21),
    "26.1.1": getattr(MCVersion, "MC_26_1_1", MCVersion.MC_1_21),
    "26.1.2": getattr(MCVersion, "MC_26_1_2", MCVersion.MC_1_21),
    "26.2": getattr(MCVersion, "MC_26_2", MCVersion.MC_1_21),
}

DIMENSION_MAP: dict[str, int] = {
    "overworld": Dimension.DIM_OVERWORLD,
    "nether": Dimension.DIM_NETHER,
    "end": Dimension.DIM_END,
}

STRUCTURE_MAP: dict[str, int] = {
    "feature": Structure.Feature[0],
    "desert_pyramid": Structure.Desert_Pyramid[0],
    "jungle_temple": Structure.Jungle_Temple[0],
    "jungle_pyramid": Structure.Jungle_Pyramid[0],
    "swamp_hut": Structure.Swamp_Hut[0],
    "igloo": Structure.Igloo[0],
    "village": Structure.Village[0],
    "ocean_ruin": Structure.Ocean_Ruin[0],
    "shipwreck": Structure.Shipwreck[0],
    "monument": Structure.Monument[0],
    "mansion": Structure.Mansion[0],
    "outpost": Structure.Outpost[0],
    "ruined_portal": Structure.Ruined_Portal[0],
    "ruined_portal_n": Structure.Ruined_Portal_N[0],
    "ancient_city": Structure.Ancient_City[0],
    "treasure": Structure.Treasure[0],
    "mineshaft": Structure.Mineshaft[0],
    "desert_well": Structure.Desert_Well[0],
    "geode": Structure.Geode[0],
    "fortress": Structure.Fortress[0],
    "bastion": Structure.Bastion[0],
    "end_city": Structure.End_City[0],
    "end_gateway": Structure.End_Gateway[0],
    "end_island": Structure.End_Island[0],
    "trail_ruin": Structure.Trail_Ruin[0],
    "trial_chambers": Structure.Trial_Chambers[0],
}

BIOME_MAP: dict[str, BiomeID] = {}
# Iterate __members__ so every alias (e.g. mushroomIsland, icePlains) is
# registered, not just the canonical enum names returned by dir().
for name, val in BiomeID.__members__.items():
    if name.startswith("_"):
        continue
    BIOME_MAP[name.lower()] = val
    BIOME_MAP[val.label.lower().replace(" ", "_")] = val

BASTION_MAP: dict[str, int] = {
    "housing": 0,
    "stables": 1,
    "treasure": 2,
    "bridge": 3,
}


def resolve_version(version: str) -> MCVersion:
    key = version.strip().lower().lstrip("mc_")
    if key not in VERSION_MAP:
        raise ValueError(f"Unsupported Minecraft version: {version}")
    return VERSION_MAP[key]


def structure_id(name: str) -> int:
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in STRUCTURE_MAP:
        raise ValueError(f"Unknown structure: {name}")
    return STRUCTURE_MAP[key]


def biome_id(name: str) -> BiomeID:
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in BIOME_MAP:
        raise ValueError(f"Unknown biome: {name}")
    return BIOME_MAP[key]


def dimension_id(name: str) -> int:
    key = name.strip().lower()
    if key not in DIMENSION_MAP:
        raise ValueError(f"Unknown dimension: {name}")
    return DIMENSION_MAP[key]


class WorldContext:
    """Cached generators per dimension for a single seed."""

    def __init__(self, version: MCVersion, seed: int):
        self.version = version
        self.seed = seed
        self._gens: dict[int, Generator] = {}
        self._spawn: tuple[int, int] | None = None
        self._strongholds: list[tuple[int, int]] = []

    def gen(self, dimension: int) -> Generator:
        if dimension not in self._gens:
            self._gens[dimension] = Generator(self.version, self.seed, dimension)
        return self._gens[dimension]

    def spawn(self) -> tuple[int, int]:
        # Spawn resolution is one of the most expensive cubiomes calls and is
        # referenced repeatedly while checking a single seed, so cache it.
        if self._spawn is None:
            self._spawn = self.gen(Dimension.DIM_OVERWORLD).get_spawn_pos()
        return self._spawn

    def strongholds(self, count: int = 128) -> list[tuple[int, int]]:
        # Stronghold positions are generated in ring order, so a cached longer
        # list already contains the answer for any smaller count.
        if len(self._strongholds) < count:
            self._strongholds = self.gen(Dimension.DIM_OVERWORLD).get_stronghold_pos(count)
        return self._strongholds[:count]

    def biome_at(self, dimension: int, x: int, y: int, z: int) -> BiomeID:
        return self.gen(dimension).get_biome_at(x, y, z)

    def closest_structure(
        self, dimension: int, structure: int, cx: int, cz: int, limit: int
    ) -> tuple[int, int] | None:
        return self.gen(dimension).find_closest_structure(structure, cx, cz, limit)

    def viable_structure(self, dimension: int, structure: int, x: int, z: int) -> bool:
        return self.gen(dimension).is_viable_structure_pos(structure, x, z)

    def structures_in_range(
        self,
        dimension: int,
        structure: int,
        x1: int,
        z1: int,
        x2: int,
        z2: int,
    ) -> list[tuple[int, int]] | None:
        return self.gen(dimension).find_structure_in_range(structure, x1, z1, x2, z2)

    def bastion_variant(self, x: int, z: int) -> int:
        return self.gen(Dimension.DIM_NETHER).get_bastion_variant(x, z)

    def end_surface_y(self, x: int, z: int) -> int:
        return self.gen(Dimension.DIM_END).get_end_y_height(x, z)


def chunk_dist(x1: int, z1: int, x2: int, z2: int) -> float:
    return distance_between_points(x1, z1, x2, z2)


def block_dist(x1: int, z1: int, x2: int, z2: int) -> float:
    return math.hypot(x2 - x1, z2 - z1)


def resolve_point(
    ctx: WorldContext, ref: str, custom: tuple[int, int] | None = None
) -> tuple[int, int]:
    ref = ref.lower()
    if ref == "spawn":
        return ctx.spawn()
    if ref == "origin" or ref == "0,0":
        return (0, 0)
    if custom is not None:
        return custom
    raise ValueError(f"Unknown point reference: {ref}")


def biome_name(biome: BiomeID | int) -> str:
    if isinstance(biome, BiomeID):
        return biome.label
    try:
        return BiomeID(biome).label
    except (ValueError, TypeError):
        return str(biome)


def collect_seed_details(ctx: WorldContext) -> dict[str, Any]:
    sx, sz = ctx.spawn()
    sh = ctx.strongholds(3)
    return {
        "spawn": (sx, sz),
        "strongholds": sh[:3],
        "spawn_biome": biome_name(ctx.biome_at(Dimension.DIM_OVERWORLD, sx, 64, sz)),
    }
