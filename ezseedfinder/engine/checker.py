"""Evaluate seed criteria against cubiomes world context."""

from __future__ import annotations

import math
from typing import Any

from cubiomespi import Dimension

from ..ezsf.ast import (
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
    StructureVariantRule,
    TerrainRule,
)
from .loot_tables import get_loot_tables, roll_chest_loot
from .variants import (
    get_bastion_info,
    get_structure_variant,
    simulate_ruined_portal,
)
from .cubiomes_backend import (
    WorldContext,
    biome_id,
    biome_name,
    block_dist,
    dimension_id,
    resolve_point,
    resolve_version,
    structure_id,
)

OCEAN_BIOMES = {
    "ocean",
    "frozen_ocean",
    "deep_ocean",
    "warm_ocean",
    "lukewarm_ocean",
    "cold_ocean",
    "deep_warm_ocean",
    "deep_lukewarm_ocean",
    "deep_cold_ocean",
    "deep_frozen_ocean",
}

MOUNTAIN_BIOMES = {
    "mountains",
    "extremehills",
    "snowy_mountains",
    "wooded_mountains",
    "gravelly_mountains",
    "jagged_peaks",
    "frozen_peaks",
    "stony_peaks",
    "windswept_hills",
}

MOB_BIOME_HINTS: dict[str, list[str]] = {
    "witch": ["swamp", "swampland", "mangrove_swamp"],
    "slime": ["swamp", "swampland", "mangrove_swamp"],
    "mooshroom": ["mushroom_fields", "mushroomisland"],
    "enderman": ["the_end", "end_highlands", "end_midlands"],
    "blaze": ["nether_wastes", "hell", "basalt_deltas", "soul_sand_valley"],
    "ghast": ["nether_wastes", "hell", "soul_sand_valley"],
    "wither_skeleton": ["nether_wastes", "hell", "soul_sand_valley"],
    "piglin": ["crimson_forest", "nether_wastes", "hell"],
    "hoglin": ["crimson_forest"],
    "endermite": ["the_end"],
    "shulker": ["end_city"],
    "guardian": ["ocean", "deep_ocean"],
    "elder_guardian": ["monument"],
    "drowned": ["river", "ocean"],
    "pillager": ["outpost"],
    "villager": ["plains", "desert", "savanna", "taiga", "snowy_taiga"],
}


class SeedChecker:
    """Check whether a seed satisfies a criteria document and GUI filters."""

    def __init__(self, doc: Document | None = None, gui_filters: dict[str, Any] | None = None):
        self.doc = doc or Document()
        self.gui_filters = gui_filters or {}
        version = self.doc.version or self.gui_filters.get("version", "26.2")
        self.version_str = version
        self.mc_version = resolve_version(version)

    def check(self, seed: int) -> tuple[bool, dict[str, Any]]:
        ctx = WorldContext(self.mc_version, seed)
        details: dict[str, Any] = {}

        if not self._check_gui(ctx, details):
            return False, details

        for stmt in self.doc.statements:
            if not self._eval_stmt(ctx, stmt, details):
                return False, details

        details.update(self._base_details(ctx))
        return True, details

    def _base_details(self, ctx: WorldContext) -> dict[str, Any]:
        sx, sz = ctx.spawn()
        return {
            "spawn": (sx, sz),
            "spawn_biome": biome_name(ctx.biome_at(Dimension.DIM_OVERWORLD, sx, 64, sz)),
            "nearest_stronghold": ctx.strongholds(1)[0] if ctx.strongholds(1) else None,
        }

    def _check_gui(self, ctx: WorldContext, details: dict[str, Any]) -> bool:
        gf = self.gui_filters
        if not gf:
            return True

        sx, sz = ctx.spawn()
        details["spawn"] = (sx, sz)

        for key, struct_name in [
            ("village_dist", "village"),
            ("desert_pyramid_dist", "desert_pyramid"),
            ("ruined_portal_dist", "ruined_portal"),
            ("mansion_dist", "mansion"),
            ("monument_dist", "monument"),
            ("outpost_dist", "outpost"),
            ("ancient_city_dist", "ancient_city"),
            ("fortress_dist", "fortress"),
            ("bastion_dist", "bastion"),
            ("end_city_dist", "end_city"),
        ]:
            if not gf.get(f"{key}_enabled", gf.get(key) is not None):
                continue
            dist = gf.get(key)
            if dist and int(dist) > 0:
                dim = "nether" if struct_name in ("fortress", "bastion") else (
                    "end" if struct_name == "end_city" else "overworld"
                )
                if not self._check_structure(
                    ctx,
                    StructureRule(dim, struct_name, "spawn", None, int(dist), True),
                    details,
                ):
                    return False

        sh_dist = gf.get("stronghold_dist")
        if gf.get("stronghold_dist_enabled", sh_dist is not None) and sh_dist and int(sh_dist) > 0:
            rule = StrongholdRule(nearest_max_dist=int(sh_dist), ref="spawn")
            if not self._eval_stronghold(ctx, rule, details):
                return False

        if gf.get("stronghold_under_spawn"):
            rule = StrongholdRule(under_player=True)
            if not self._eval_stronghold(ctx, rule, details):
                return False

        if gf.get("stronghold_full"):
            rule = StrongholdRule(full=True)
            if not self._eval_stronghold(ctx, rule, details):
                return False

        spawn_biome = gf.get("spawn_biome")
        if gf.get("spawn_biome_enabled", bool(spawn_biome)) and spawn_biome:
            rule = SpawnRule(biomes=[spawn_biome])
            if not self._eval_spawn(ctx, rule, details):
                return False

        spawn_max = gf.get("spawn_max_dist")
        if gf.get("spawn_dist_enabled", bool(spawn_max)) and spawn_max and int(spawn_max) > 0:
            if block_dist(sx, sz, 0, 0) > int(spawn_max):
                return False

        return True

    def _eval_stmt(self, ctx: WorldContext, stmt: Any, details: dict[str, Any]) -> bool:
        if isinstance(stmt, DimensionBlock):
            return all(self._eval_stmt(ctx, s, details) for s in stmt.statements)
        if isinstance(stmt, BiomeAt):
            return self._eval_biome_at(ctx, stmt, details)
        if isinstance(stmt, StructureVariantRule):
            return self._eval_structure_variant(ctx, stmt, details)
        if isinstance(stmt, StructureRule):
            return self._check_structure(ctx, stmt, details)
        if isinstance(stmt, StructureBetween):
            return self._eval_structure_between(ctx, stmt, details)
        if isinstance(stmt, StrongholdRule):
            return self._eval_stronghold(ctx, stmt, details)
        if isinstance(stmt, SpawnRule):
            return self._eval_spawn(ctx, stmt, details)
        if isinstance(stmt, BastionRule):
            return self._eval_bastion(ctx, stmt, details)
        if isinstance(stmt, BiomeRegion):
            return self._eval_biome_region(ctx, stmt, details)
        if isinstance(stmt, DistanceRule):
            return self._eval_distance(ctx, stmt, details)
        if isinstance(stmt, TerrainRule):
            return self._eval_terrain(ctx, stmt, details)
        if isinstance(stmt, HeightRule):
            return self._eval_height(ctx, stmt, details)
        if isinstance(stmt, RuinedPortalRule):
            return self._eval_ruined_portal(ctx, stmt, details)
        if isinstance(stmt, LootRule):
            return self._eval_loot(ctx, stmt, details)
        if isinstance(stmt, MobRule):
            return self._eval_mob(ctx, stmt, details)
        return True

    def _eval_biome_at(self, ctx: WorldContext, rule: BiomeAt, details: dict[str, Any]) -> bool:
        dim = dimension_id(rule.dimension)
        x, z = rule.x, rule.z
        if x == -1 and z == -1:
            x, z = ctx.spawn()
        biome = ctx.biome_at(dim, x, rule.y, z)
        names = {biome_id(b).value for b in rule.biomes}
        match = biome.value in names or biome in [biome_id(b) for b in rule.biomes]
        ok = not match if rule.negate else match
        if ok:
            details[f"biome_at_{rule.x}_{rule.z}"] = biome_name(biome)
        return ok

    def _eval_biome_region(self, ctx: WorldContext, rule: BiomeRegion, details: dict[str, Any]) -> bool:
        dim = dimension_id(rule.dimension)
        target = biome_id(rule.biome)
        step = 32
        total = 0
        hits = 0
        for x in range(min(rule.x1, rule.x2), max(rule.x1, rule.x2) + 1, step):
            for z in range(min(rule.z1, rule.z2), max(rule.z1, rule.z2) + 1, step):
                total += 1
                b = ctx.biome_at(dim, x, rule.y, z)
                if b == target:
                    hits += 1
        pct = (hits / total * 100) if total else 0
        if rule.op == "contains":
            ok = hits > 0
        elif rule.op == "==":
            ok = hits == total
        elif rule.op == ">=":
            ok = pct >= (rule.percent or 0)
        elif rule.op == "<=":
            ok = pct <= (rule.percent or 100)
        else:
            ok = hits > 0
        if ok:
            details[f"biome_region_{rule.biome}"] = f"{pct:.1f}%"
        return ok

    def _check_structure(
        self, ctx: WorldContext, rule: StructureRule, details: dict[str, Any]
    ) -> bool:
        dim = dimension_id(rule.dimension)
        struct = structure_id(rule.structure)
        px, pz = resolve_point(ctx, rule.ref, rule.ref_pos)
        limit = max(rule.max_dist // 16, 1)
        pos = ctx.closest_structure(dim, struct, px, pz, limit)
        if pos is None:
            return False
        dist = block_dist(px, pz, pos[0], pos[1])
        if dist > rule.max_dist:
            return False
        if rule.viable and not ctx.viable_structure(dim, struct, pos[0], pos[1]):
            return False
        details[f"{rule.structure}_pos"] = pos
        details[f"{rule.structure}_dist"] = round(dist)
        return True

    def _eval_structure_between(
        self, ctx: WorldContext, rule: StructureBetween, details: dict[str, Any]
    ) -> bool:
        dim = dimension_id(rule.dimension)
        sa = structure_id(rule.structure_a)
        sb = structure_id(rule.structure_b)
        px, pz = resolve_point(ctx, rule.ref, rule.ref_pos)
        limit = max(rule.max_dist // 16, 1)
        pa = ctx.closest_structure(dim, sa, px, pz, limit)
        pb = ctx.closest_structure(dim, sb, px, pz, limit)
        if pa is None or pb is None:
            return False
        if rule.viable:
            if not ctx.viable_structure(dim, sa, pa[0], pa[1]):
                return False
            if not ctx.viable_structure(dim, sb, pb[0], pb[1]):
                return False
        dist = block_dist(pa[0], pa[1], pb[0], pb[1])
        ok = dist <= rule.max_dist
        if ok:
            details[f"{rule.structure_a}_and_{rule.structure_b}_dist"] = round(dist)
        return ok

    def _eval_stronghold(self, ctx: WorldContext, rule: StrongholdRule, details: dict[str, Any]) -> bool:
        strongholds = ctx.strongholds(rule.count)
        if not strongholds:
            return False

        sx, sz = ctx.spawn()

        if rule.nearest_max_dist is not None:
            px, pz = resolve_point(ctx, rule.ref, rule.ref_pos)
            nearest = min(strongholds, key=lambda p: block_dist(px, pz, p[0], p[1]))
            dist = block_dist(px, pz, nearest[0], nearest[1])
            if dist > rule.nearest_max_dist:
                return False
            details["stronghold_nearest"] = nearest
            details["stronghold_dist"] = round(dist)

        if rule.under_player:
            # Stronghold "under" spawn: within ~200 blocks and ring 1 preferred
            nearest = min(strongholds, key=lambda p: block_dist(sx, sz, p[0], p[1]))
            dist = block_dist(sx, sz, nearest[0], nearest[1])
            if dist > 250:
                return False
            details["stronghold_under_spawn"] = nearest

        if rule.full:
            # Full stronghold requires all 128 portal rooms — approximated by
            # ring-1 stronghold within reasonable distance of origin.
            ring1 = [sh for sh in strongholds[:16]]
            if not ring1:
                return False
            nearest = min(ring1, key=lambda p: block_dist(0, 0, p[0], p[1]))
            if block_dist(0, 0, nearest[0], nearest[1]) > 2500:
                return False
            details["stronghold_full_approx"] = nearest

        if rule.ring is not None:
            idx = max(0, rule.ring - 1)
            if idx >= len(strongholds):
                return False
            details[f"stronghold_ring_{rule.ring}"] = strongholds[idx]

        return True

    def _eval_spawn(self, ctx: WorldContext, rule: SpawnRule, details: dict[str, Any]) -> bool:
        sx, sz = ctx.spawn()
        if rule.max_dist is not None:
            px, pz = resolve_point(ctx, rule.ref, rule.ref_pos)
            if block_dist(sx, sz, px, pz) > rule.max_dist:
                return False
        if rule.biomes:
            biome = ctx.biome_at(Dimension.DIM_OVERWORLD, sx, 64, sz)
            names = {biome_id(b) for b in rule.biomes}
            if biome not in names:
                return False
            details["spawn_biome"] = biome_name(biome)
        details["spawn"] = (sx, sz)
        return True

    def _eval_bastion(self, ctx: WorldContext, rule: BastionRule, details: dict[str, Any]) -> bool:
        px, pz = resolve_point(ctx, rule.ref, rule.ref_pos)
        struct = structure_id("bastion")
        limit = max(rule.max_dist // 16, 1)
        pos = ctx.closest_structure(Dimension.DIM_NETHER, struct, px, pz, limit)
        if pos is None:
            return False
        dist = block_dist(px, pz, pos[0], pos[1])
        if dist > rule.max_dist:
            return False
        if rule.viable and not ctx.viable_structure(Dimension.DIM_NETHER, struct, pos[0], pos[1]):
            return False
        info = get_bastion_info(self.mc_version, ctx.seed, pos[0], pos[1])
        if info is None:
            return False
        if rule.variant.lower() != info.variant:
            return False
        details["bastion_pos"] = pos
        details["bastion_variant"] = info.variant
        details["bastion_rotation"] = info.rotation
        return True

    def _eval_structure_variant(
        self, ctx: WorldContext, rule: StructureVariantRule, details: dict[str, Any]
    ) -> bool:
        dim = dimension_id(rule.dimension)
        struct = structure_id(rule.structure)
        px, pz = resolve_point(ctx, rule.ref, rule.ref_pos)
        limit = max(rule.max_dist // 16, 1)
        pos = ctx.closest_structure(dim, struct, px, pz, limit)
        if pos is None:
            return False
        if rule.viable and not ctx.viable_structure(dim, struct, pos[0], pos[1]):
            return False
        if rule.bastion_variant:
            info = get_bastion_info(self.mc_version, ctx.seed, pos[0], pos[1])
            if info is None or info.variant != rule.bastion_variant.lower():
                return False
            details["bastion_variant"] = info.variant
        if rule.structure == "village" and rule.village_abandoned is not None:
            biome = ctx.biome_at(dim, pos[0], 64, pos[1])
            sv = get_structure_variant(struct, self.mc_version, ctx.seed, pos[0], pos[1], biome)
            if sv is None or bool(sv.abandoned) != rule.village_abandoned:
                return False
            details["village_abandoned"] = sv.abandoned
        details[f"{rule.structure}_pos"] = pos
        return True

    def _eval_distance(self, ctx: WorldContext, rule: DistanceRule, details: dict[str, Any]) -> bool:
        dim = dimension_id(rule.dimension)
        if rule.kind == "structures" and rule.b:
            sa = structure_id(rule.a)
            sb = structure_id(rule.b)
            limit = max(int(rule.max_search) // 16, 1)
            cx, cz = (0, 0)
            if rule.ref:
                cx, cz = resolve_point(ctx, rule.ref, rule.ref_pos)
            pa = ctx.closest_structure(dim, sa, cx, cz, limit)
            pb = ctx.closest_structure(dim, sb, cx, cz, limit)
            if pa is None or pb is None:
                return False
            dist = block_dist(pa[0], pa[1], pb[0], pb[1])
        else:
            return True
        ok = self._compare(dist, rule.op, rule.value)
        if ok:
            details[f"distance_{rule.a}_{rule.b}"] = round(dist)
        return ok

    def _eval_terrain(self, ctx: WorldContext, rule: TerrainRule, details: dict[str, Any]) -> bool:
        dim = dimension_id(rule.dimension)
        ocean = mountain = flat = 0
        total = 0
        step = max(rule.radius // 4, 8)
        for dx in range(-rule.radius, rule.radius + 1, step):
            for dz in range(-rule.radius, rule.radius + 1, step):
                total += 1
                b = ctx.biome_at(dim, rule.x + dx, 64, rule.z + dz)
                name = biome_name(b).lower().replace(" ", "_")
                if name in OCEAN_BIOMES or "ocean" in name:
                    ocean += 1
                elif name in MOUNTAIN_BIOMES or "peak" in name or "mountain" in name:
                    mountain += 1
                else:
                    flat += 1
        pred = rule.predicate.lower()
        if pred == "oceanic":
            ok = ocean > total * 0.4
        elif pred == "mountainous":
            ok = mountain > total * 0.3
        elif pred == "flat":
            ok = flat > total * 0.7
        else:
            ok = True
        if rule.negate:
            ok = not ok
        return ok

    def _eval_height(self, ctx: WorldContext, rule: HeightRule, details: dict[str, Any]) -> bool:
        dim = dimension_id(rule.dimension)
        if dim == Dimension.DIM_END:
            y = ctx.end_surface_y(rule.x, rule.z)
        else:
            # Approximate surface via biome noise isn't in cubiomes wrapper;
            # use y=64 check biome as terrain height proxy for overworld/nether.
            y = 64
        return self._compare(y, rule.op, rule.value)

    def _eval_ruined_portal(self, ctx: WorldContext, rule: RuinedPortalRule, details: dict[str, Any]) -> bool:
        dim = dimension_id(rule.dimension)
        struct = (
            structure_id("ruined_portal_n")
            if dim == Dimension.DIM_NETHER
            else structure_id("ruined_portal")
        )
        px, pz = resolve_point(ctx, rule.ref, rule.ref_pos)
        limit = max(rule.max_dist // 16, 1)
        pos = ctx.closest_structure(dim, struct, px, pz, limit)
        if pos is None:
            return False
        dist = block_dist(px, pz, pos[0], pos[1])
        if dist > rule.max_dist:
            return False
        if rule.viable and not ctx.viable_structure(dim, struct, pos[0], pos[1]):
            return False

        biome = ctx.biome_at(dim, pos[0], 64, pos[1]).value
        portal = simulate_ruined_portal(
            self.mc_version,
            ctx.seed,
            pos[0],
            pos[1],
            biome,
            game_version=self.version_str,
            roll_loot=bool(rule.chest_items),
        )
        if portal is None:
            return False

        sv = get_structure_variant(struct, self.mc_version, ctx.seed, pos[0], pos[1], biome)
        if sv is None:
            return False

        if rule.giant is not None and sv.giant != rule.giant:
            return False
        if rule.underground is not None and sv.underground != rule.underground:
            return False
        if rule.airpocket is not None and sv.airpocket != rule.airpocket:
            return False
        if rule.template is not None and sv.start != rule.template:
            return False
        if rule.top_missing is not None and portal.top_missing != rule.top_missing:
            return False
        if rule.frame_missing is not None and portal.frame_missing != rule.frame_missing:
            return False
        elif rule.top_missing is not None and not portal.missing_top_only(rule.top_missing):
            return False

        if rule.chest_items and portal.loot:
            for item, min_count in rule.chest_items:
                key = item.lower().replace("-", "_")
                if portal.loot.count(key) < min_count:
                    return False

        details["ruined_portal_pos"] = pos
        details["ruined_portal_template"] = portal.template
        details["ruined_portal_top_missing"] = portal.top_missing
        details["ruined_portal_frame_missing"] = portal.frame_missing
        details["ruined_portal_non_top_missing"] = portal.non_top_missing
        if portal.loot:
            details["ruined_portal_chest"] = dict(portal.loot.items)
        return True

    def _eval_loot(self, ctx: WorldContext, rule: LootRule, details: dict[str, Any]) -> bool:
        dim = dimension_id(rule.dimension)
        struct_name = rule.structure.lower()
        px, pz = resolve_point(ctx, rule.ref, rule.ref_pos)
        limit = max(rule.max_dist // 16, 1)
        struct = structure_id(struct_name)
        pos = ctx.closest_structure(dim, struct, px, pz, limit)
        if pos is None:
            return False

        if struct_name in ("ruined_portal", "ruined_portal_n"):
            biome = ctx.biome_at(dim, pos[0], 64, pos[1]).value
            portal = simulate_ruined_portal(
                self.mc_version,
                ctx.seed,
                pos[0],
                pos[1],
                biome,
                game_version=self.version_str,
            )
            if portal is None or portal.loot is None:
                return False
            if not portal.loot.has(rule.item.lower(), rule.min_count):
                return False
            details["loot_chest"] = dict(portal.loot.items)
            details["loot_structure_pos"] = pos
            return True

        if struct_name in ("treasure", "buried_treasure"):
            table = rule.loot_table or "buried_treasure"
            loot = roll_chest_loot(table, self.version_str, ctx.seed, pos[0], 64, pos[1])
            if not loot.has(rule.item.lower(), rule.min_count):
                return False
            details["loot_chest"] = dict(loot.items)
            details["loot_structure_pos"] = pos
            return True

        if struct_name in ("shipwreck",):
            table = rule.loot_table or "shipwreck_treasure"
            loot = roll_chest_loot(table, self.version_str, ctx.seed, pos[0], 64, pos[1])
            if not loot.has(rule.item.lower(), rule.min_count):
                return False
            details["loot_chest"] = dict(loot.items)
            details["loot_structure_pos"] = pos
            return True

        if not ctx.viable_structure(dim, struct, pos[0], pos[1]):
            return False
        table = rule.loot_table
        if table and table in get_loot_tables(self.version_str):
            loot = roll_chest_loot(table, self.version_str, ctx.seed, pos[0], 64, pos[1])
            if not loot.has(rule.item.lower(), rule.min_count):
                return False
            details["loot_chest"] = dict(loot.items)
            details["loot_structure_pos"] = pos
            return True
        details["loot_note"] = (
            f"Structure {struct_name} present; chest loot for '{rule.item}' "
            "not simulated for this structure type yet"
        )
        return True

    def _eval_mob(self, ctx: WorldContext, rule: MobRule, details: dict[str, Any]) -> bool:
        dim = dimension_id(rule.dimension)
        px, pz = resolve_point(ctx, rule.ref, rule.ref_pos)
        biomes = rule.biomes or MOB_BIOME_HINTS.get(rule.mob.lower(), [])
        if not biomes:
            return True
        step = max(rule.max_dist // 8, 16)
        for dx in range(-rule.max_dist, rule.max_dist + 1, step):
            for dz in range(-rule.max_dist, rule.max_dist + 1, step):
                x, z = px + dx, pz + dz
                if block_dist(px, pz, x, z) > rule.max_dist:
                    continue
                b = ctx.biome_at(dim, x, 64, z)
                name = biome_name(b).lower().replace(" ", "_")
                if any(name == biome_id(bn).name.lower() for bn in biomes):
                    details[f"mob_{rule.mob}_biome"] = name
                    return True
        return False

    @staticmethod
    def _compare(value: float, op: str, target: float) -> bool:
        if op in ("<=", "=<"):
            return value <= target
        if op in (">=", "=>"):
            return value >= target
        if op == "<":
            return value < target
        if op == ">":
            return value > target
        if op == "==":
            return math.isclose(value, target, rel_tol=0, abs_tol=1)
        return False
