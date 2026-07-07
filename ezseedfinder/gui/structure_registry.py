"""Structure kinds and per-type GUI/ezsf metadata."""

from __future__ import annotations

STRUCTURE_KINDS: dict[str, str] = {
    "ruined_portal": "portal",
    "bastion": "bastion",
    "treasure": "loot_chest",
    "shipwreck": "loot_chest",
}

STRUCTURE_LOOT_TABLE: dict[str, str] = {
    "treasure": "buried_treasure",
    "shipwreck": "shipwreck_treasure",
}

DEFAULT_DIST: dict[str, str] = {
    "village": "500",
    "treasure": "800",
    "ruined_portal": "500",
    "bastion": "600",
    "fortress": "600",
}


def structure_kind(name: str) -> str:
    return STRUCTURE_KINDS.get(name, "simple")


def default_dist(name: str) -> str:
    return DEFAULT_DIST.get(name, "0")
