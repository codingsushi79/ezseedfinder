"""Chest loot simulation for common structure tables (Minecraft 1.16.1)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .java_random import JavaRandom


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
class LootResult:
    items: dict[str, int] = field(default_factory=dict)

    def count(self, item: str) -> int:
        return self.items.get(item, 0)

    def has(self, item: str, min_count: int = 1) -> bool:
        return self.count(item) >= min_count


RUINED_PORTAL_LOOT = LootPool(
    min_rolls=4,
    max_rolls=8,
    entries=[
        LootEntry("obsidian", 40, 1, 2),
        LootEntry("flint", 40, 1, 4),
        LootEntry("iron_nugget", 40, 9, 18),
        LootEntry("flint_and_steel", 40),
        LootEntry("fire_charge", 40),
        LootEntry("golden_apple", 15),
        LootEntry("gold_nugget", 15, 4, 24),
        LootEntry("golden_sword", 15),
        LootEntry("golden_axe", 15),
        LootEntry("golden_hoe", 15),
        LootEntry("golden_shovel", 15),
        LootEntry("golden_pickaxe", 15),
        LootEntry("golden_boots", 15),
        LootEntry("golden_chestplate", 15),
        LootEntry("golden_helmet", 15),
        LootEntry("golden_leggings", 15),
        LootEntry("glistering_melon_slice", 5, 4, 12),
        LootEntry("golden_horse_armor", 5),
        LootEntry("light_weighted_pressure_plate", 5),
        LootEntry("golden_carrot", 5, 4, 12),
        LootEntry("clock", 5),
        LootEntry("gold_ingot", 5, 2, 8),
        LootEntry("bell", 1),
        LootEntry("enchanted_golden_apple", 1),
        LootEntry("gold_block", 1, 1, 2),
    ],
)

BURIED_TREASURE_LOOT = LootPool(
    min_rolls=5,
    max_rolls=8,
    entries=[
        LootEntry("heart_of_the_sea", 5),
        LootEntry("iron_ingot", 20, 1, 4),
        LootEntry("gold_ingot", 20, 1, 4),
        LootEntry("tnt", 20, 1, 2),
        LootEntry("emerald", 15, 4, 8),
        LootEntry("diamond", 5, 1, 2),
        LootEntry("prismarine_crystals", 5, 1, 5),
        LootEntry("prismarine_shard", 5, 1, 5),
        LootEntry("cooked_cod", 10, 2, 4),
        LootEntry("cooked_salmon", 10, 2, 4),
        LootEntry("potion", 10),
        LootEntry("iron_sword", 10),
        LootEntry("leather_chestplate", 10),
        LootEntry("gold_block", 5, 1, 2),
        LootEntry("iron_block", 5, 1, 2),
        LootEntry("diamond_block", 1),
    ],
)

SHIPWRECK_TREASURE_LOOT = LootPool(
    min_rolls=3,
    max_rolls=6,
    entries=[
        LootEntry("iron_ingot", 90, 1, 5),
        LootEntry("gold_ingot", 10, 1, 5),
        LootEntry("emerald", 40, 1, 5),
        LootEntry("diamond", 5, 1, 5),
        LootEntry("lapis_lazuli", 20, 1, 5),
        LootEntry("iron_nugget", 50, 1, 10),
        LootEntry("gold_nugget", 50, 1, 10),
        LootEntry("diamond_block", 1),
    ],
)

LOOT_TABLES: dict[str, LootPool] = {
    "ruined_portal": RUINED_PORTAL_LOOT,
    "buried_treasure": BURIED_TREASURE_LOOT,
    "shipwreck_treasure": SHIPWRECK_TREASURE_LOOT,
}

LOOT_TABLE_NAMES = tuple(LOOT_TABLES.keys())


def _roll_uniform(rng: JavaRandom, lo: float, hi: float) -> int:
    if lo == hi:
        return int(lo)
    return int(rng.next_int(int(hi - lo) + 1) + int(lo))


def roll_loot_pool(rng: JavaRandom, pool: LootPool) -> LootResult:
    result = LootResult()
    rolls = _roll_uniform(rng, pool.min_rolls, pool.max_rolls)
    total_weight = sum(e.weight for e in pool.entries)
    for _ in range(rolls):
        roll = rng.next_int(total_weight)
        acc = 0
        for entry in pool.entries:
            acc += entry.weight
            if roll < acc:
                count = _roll_uniform(rng, entry.min_count, entry.max_count)
                result.items[entry.item] = result.items.get(entry.item, 0) + count
                break
    return result


def roll_chest_loot(
    table: str,
    world_seed: int,
    x: int,
    y: int,
    z: int,
) -> LootResult:
    from .java_random import chest_loot_seed

    pool = LOOT_TABLES.get(table)
    if pool is None:
        return LootResult()
    rng = JavaRandom(chest_loot_seed(world_seed, x, y, z))
    return roll_loot_pool(rng, pool)


def roll_ruined_portal_chest(world_seed: int, x: int, y: int, z: int) -> LootResult:
    return roll_chest_loot("ruined_portal", world_seed, x, y, z)
