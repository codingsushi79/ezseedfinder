"""Structure kinds and per-type GUI/ezsf metadata."""

from __future__ import annotations

STRUCTURE_KINDS: dict[str, str] = {
    "ruined_portal": "portal",
    "bastion": "bastion",
    "treasure": "loot_chest",
    "shipwreck": "loot_chest",
    "desert_pyramid": "loot_chest",
    "jungle_temple": "loot_chest",
    "ancient_city": "loot_chest",
    "trail_ruin": "loot_chest",
}

STRUCTURE_LOOT_TABLE: dict[str, str] = {
    "treasure": "buried_treasure",
    "shipwreck": "shipwreck_treasure",
    "desert_pyramid": "desert_pyramid",
    "jungle_temple": "jungle_temple",
    "ancient_city": "ancient_city",
    "trail_ruin": "trail_ruins",
    "bastion": "bastion_treasure",
}

DEFAULT_DIST: dict[str, str] = {
    "village": "500",
    "treasure": "800",
    "ruined_portal": "500",
    "bastion": "600",
    "fortress": "600",
    "desert_pyramid": "500",
    "jungle_temple": "500",
    "ancient_city": "800",
    "trail_ruin": "600",
}


def structure_kind(name: str) -> str:
    return STRUCTURE_KINDS.get(name, "simple")


def default_dist(name: str) -> str:
    return DEFAULT_DIST.get(name, "0")
