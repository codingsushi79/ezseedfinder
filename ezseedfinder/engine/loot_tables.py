"""Version-aware chest loot simulation from bundled vanilla loot table data."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from .java_random import JavaRandom

_DATA_DIR = Path(__file__).with_name("loot_data")

# GUI / search version -> misode mcmeta data-json tag (when fetching)
MCMETA_VERSION_TAGS: dict[str, str] = {
    "1.16": "1.16.1",
    "1.16.1": "1.16.1",
    "1.16.5": "1.16.5",
    "1.17.1": "1.17.1",
    "1.18.2": "1.18.2",
    "1.19": "1.19.2",
    "1.19.2": "1.19.2",
    "1.20": "1.20.6",
    "1.21": "1.21.11",
    "26.1": "26.1.2",
    "26.1.1": "26.1.2",
    "26.1.2": "26.1.2",
    "26.2": "26.2",
}

VANILLA_TABLE_FILES: dict[str, str] = {
    "ruined_portal": "chests/ruined_portal.json",
    "buried_treasure": "chests/buried_treasure.json",
    "shipwreck_treasure": "chests/shipwreck_treasure.json",
}


@dataclass
class LootEntry:
    item: str
    weight: int
    min_count: int = 1
    max_count: int = 1


@dataclass
class LootPool:
    min_rolls: float
    max_rolls: float
    entries: list[LootEntry]


@dataclass
class LootTableData:
    pools: list[LootPool]


@dataclass
class LootResult:
    items: dict[str, int] = field(default_factory=dict)

    def count(self, item: str) -> int:
        return self.items.get(item, 0)

    def has(self, item: str, min_count: int = 1) -> bool:
        return self.count(item) >= min_count


def _parse_version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in version.strip().lower().lstrip("mc_").split("."):
        if not piece:
            continue
        digits = ""
        for ch in piece:
            if ch.isdigit():
                digits += ch
            else:
                break
        if digits:
            parts.append(int(digits))
    return tuple(parts) if parts else (0,)


def normalize_loot_version(version: str) -> str:
    key = version.strip().lower().lstrip("mc_")
    return MCMETA_VERSION_TAGS.get(key, key)


def list_loot_data_versions() -> list[str]:
    if not _DATA_DIR.is_dir():
        return []
    return sorted(
        (p.stem for p in _DATA_DIR.glob("*.json")),
        key=_parse_version_tuple,
    )


def resolve_loot_data_version(version: str) -> str:
    """Pick bundled loot data for an exact or nearest lower game version."""
    requested = normalize_loot_version(version)
    available = list_loot_data_versions()
    if not available:
        raise FileNotFoundError("No bundled loot table data found")
    if requested in available:
        return requested
    req_tuple = _parse_version_tuple(requested)
    best = available[0]
    for candidate in available:
        if _parse_version_tuple(candidate) <= req_tuple:
            best = candidate
        else:
            break
    return best


def _pool_from_dict(data: dict[str, Any]) -> LootPool:
    return LootPool(
        min_rolls=float(data["min_rolls"]),
        max_rolls=float(data["max_rolls"]),
        entries=[
            LootEntry(
                item=e["item"],
                weight=int(e["weight"]),
                min_count=int(e.get("min_count", 1)),
                max_count=int(e.get("max_count", 1)),
            )
            for e in data["entries"]
        ],
    )


def _table_from_dict(data: dict[str, Any]) -> LootTableData:
    if "pools" in data:
        return LootTableData(pools=[_pool_from_dict(p) for p in data["pools"]])
    return LootTableData(pools=[_pool_from_dict(data)])


def _table_to_dict(table: LootTableData) -> dict[str, Any]:
    return {
        "pools": [
            {
                "min_rolls": pool.min_rolls,
                "max_rolls": pool.max_rolls,
                "entries": [
                    {
                        "item": e.item,
                        "weight": e.weight,
                        "min_count": e.min_count,
                        "max_count": e.max_count,
                    }
                    for e in pool.entries
                ],
            }
            for pool in table.pools
        ]
    }


@lru_cache(maxsize=32)
def _load_version_file(data_version: str) -> dict[str, LootTableData]:
    path = _DATA_DIR / f"{data_version}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing loot data for Minecraft {data_version}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {name: _table_from_dict(body) for name, body in raw.items()}


def get_loot_tables(version: str) -> dict[str, LootTableData]:
    data_version = resolve_loot_data_version(version)
    return _load_version_file(data_version)


def loot_data_version(version: str) -> str:
    return resolve_loot_data_version(version)


def loot_table_names(version: str) -> tuple[str, ...]:
    return tuple(get_loot_tables(version).keys())


def loot_table_item_names(version: str, table: str) -> tuple[str, ...]:
    loot_table = get_loot_tables(version).get(table)
    if loot_table is None:
        return ()
    names: list[str] = []
    seen: set[str] = set()
    for pool in loot_table.pools:
        for entry in pool.entries:
            if entry.item == "empty" or entry.item in seen:
                continue
            seen.add(entry.item)
            names.append(entry.item)
    return tuple(sorted(names))


def _roll_uniform(rng: JavaRandom, lo: float, hi: float) -> int:
    if lo == hi:
        return int(lo)
    return int(rng.next_int(int(hi - lo) + 1) + int(lo))


def roll_loot_pool(rng: JavaRandom, pool: LootPool) -> LootResult:
    result = LootResult()
    rolls = _roll_uniform(rng, pool.min_rolls, pool.max_rolls)
    total_weight = sum(e.weight for e in pool.entries)
    if total_weight <= 0:
        return result
    for _ in range(rolls):
        roll = rng.next_int(total_weight)
        acc = 0
        for entry in pool.entries:
            acc += entry.weight
            if roll < acc:
                if entry.item != "empty":
                    count = _roll_uniform(rng, entry.min_count, entry.max_count)
                    result.items[entry.item] = result.items.get(entry.item, 0) + count
                break
    return result


def roll_loot_table(rng: JavaRandom, table: LootTableData) -> LootResult:
    result = LootResult()
    for pool in table.pools:
        partial = roll_loot_pool(rng, pool)
        for item, count in partial.items.items():
            result.items[item] = result.items.get(item, 0) + count
    return result


def roll_chest_loot(
    table: str,
    game_version: str,
    world_seed: int,
    x: int,
    y: int,
    z: int,
) -> LootResult:
    from .java_random import chest_loot_seed

    tables = get_loot_tables(game_version)
    loot_table = tables.get(table)
    if loot_table is None:
        return LootResult()
    rng = JavaRandom(chest_loot_seed(world_seed, x, y, z))
    return roll_loot_table(rng, loot_table)


def roll_ruined_portal_chest(
    game_version: str,
    world_seed: int,
    x: int,
    y: int,
    z: int,
) -> LootResult:
    return roll_chest_loot("ruined_portal", game_version, world_seed, x, y, z)


# --- Vanilla JSON import (used by scripts/fetch_loot_tables.py) ---


def _parse_rolls(rolls: Any) -> tuple[float, float]:
    if isinstance(rolls, (int, float)):
        return float(rolls), float(rolls)
    if isinstance(rolls, dict):
        if rolls.get("type") == "minecraft:uniform":
            return float(rolls["min"]), float(rolls["max"])
        if "min" in rolls and "max" in rolls:
            return float(rolls["min"]), float(rolls["max"])
    return 1.0, 1.0


def _parse_count(functions: list[dict[str, Any]] | None) -> tuple[int, int]:
    for fn in functions or []:
        name = fn.get("function", "")
        if name not in ("minecraft:set_count", "set_count"):
            continue
        count = fn.get("count", 1)
        if isinstance(count, dict):
            if count.get("type") == "minecraft:uniform":
                return int(count["min"]), int(count["max"])
            if "min" in count and "max" in count:
                return int(count["min"]), int(count["max"])
        return int(count), int(count)
    return 1, 1


def parse_vanilla_loot_table(data: dict[str, Any]) -> LootTableData:
    pools: list[LootPool] = []
    for pool in data.get("pools", []):
        min_rolls, max_rolls = _parse_rolls(pool.get("rolls", 1))
        entries: list[LootEntry] = []
        for entry in pool.get("entries", []):
            if entry.get("type") != "minecraft:item":
                if entry.get("type") == "minecraft:empty":
                    entries.append(LootEntry("empty", int(entry.get("weight", 1))))
                continue
            item = str(entry.get("name", "")).replace("minecraft:", "")
            if not item:
                continue
            min_count, max_count = _parse_count(entry.get("functions"))
            entries.append(
                LootEntry(
                    item=item,
                    weight=int(entry.get("weight", 1)),
                    min_count=min_count,
                    max_count=max_count,
                )
            )
        if entries:
            pools.append(LootPool(min_rolls=min_rolls, max_rolls=max_rolls, entries=entries))
    return LootTableData(pools=pools)


def export_version_loot_tables(tables: dict[str, LootTableData]) -> dict[str, Any]:
    return {name: _table_to_dict(table) for name, table in tables.items()}


def write_version_loot_file(version: str, tables: dict[str, LootTableData]) -> Path:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _DATA_DIR / f"{version}.json"
    path.write_text(
        json.dumps(export_version_loot_tables(tables), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _load_version_file.cache_clear()
    return path
