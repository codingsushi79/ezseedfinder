"""Parse .ezsf text into GUI criteria and apply to the app."""

from __future__ import annotations

from typing import Any

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
    TerrainRule,
)
from ..ezsf.parser import parse_ezsf
from .criteria_widgets import set_ref
from .structure_registry import STRUCTURE_LOOT_TABLE, structure_kind


FEATURE_KEYS = ("structures", "spawn", "biomes", "terrain", "loot")


def _empty_criteria() -> dict[str, Any]:
    return {
        "emit_version": False,
        "threads": "",
        "max_results": "",
        "seed_start": None,
        "seed_end": None,
        "random_search": True,
        "spawn": {
            "enabled": False,
            "ref": "origin",
            "ref_pos": None,
            "max_dist": "0",
            "biomes": "",
        },
        "stronghold": {
            "enabled": False,
            "nearest_enabled": False,
            "nearest_dist": "1500",
            "nearest_ref": "spawn",
            "nearest_ref_pos": None,
            "under_spawn": False,
            "full": False,
            "ring": None,
        },
        "structures": [],
        "ruined_portal": {
            "enabled": False,
            "dimension": "overworld",
            "ref": "spawn",
            "ref_pos": None,
            "max_dist": "500",
            "viable": True,
            "giant": None,
            "template": None,
            "underground": None,
            "airpocket": None,
            "top_missing": "",
            "frame_missing": "",
            "loot_table": "ruined_portal",
            "chest_items": [],
        },
        "bastion": {
            "enabled": False,
            "variant": "treasure",
            "ref": "0,0",
            "ref_pos": None,
            "max_dist": "600",
            "viable": True,
        },
        "biomes": [],
        "biome_regions": [],
        "terrain": [],
        "heights": [],
        "loot": [],
        "mobs": [],
        "structure_between": [],
        "distance_rules": [],
    }


def _ref_to_gui(ref: str, ref_pos: tuple[int, int] | None) -> tuple[str, tuple[int, int] | None]:
    if ref_pos is not None:
        return ref, ref_pos
    if ref in ("spawn", "origin"):
        return ref, None
    if ref in ("0,0", "0, 0"):
        return "origin", (0, 0)
    return ref, None


def _biomes_to_str(biomes: list[str]) -> str:
    return " | ".join(biomes)


def document_to_criteria(doc: Document) -> tuple[dict[str, Any], set[str]]:
    criteria = _empty_criteria()
    features: set[str] = set()

    if doc.threads is not None:
        criteria["threads"] = str(doc.threads)
    if doc.max_results is not None:
        criteria["max_results"] = str(doc.max_results)
    if doc.version:
        criteria["version"] = doc.version
    if doc.seed_start is not None:
        criteria["seed_start"] = str(doc.seed_start)
    if doc.seed_end is not None:
        criteria["seed_end"] = str(doc.seed_end)
    criteria["random_search"] = doc.random_search

    structures: list[dict[str, Any]] = []

    def handle(stmt: Any, dimension: str = "overworld") -> None:
        if isinstance(stmt, SpawnRule):
            features.add("spawn")
            ref, ref_pos = _ref_to_gui(stmt.ref, stmt.ref_pos)
            criteria["spawn"] = {
                "enabled": stmt.max_dist is not None or bool(stmt.biomes),
                "ref": ref,
                "ref_pos": ref_pos,
                "max_dist": str(stmt.max_dist or 0),
                "biomes": _biomes_to_str(stmt.biomes),
            }
        elif isinstance(stmt, StrongholdRule):
            features.add("spawn")
            ref, ref_pos = _ref_to_gui(stmt.ref, stmt.ref_pos)
            criteria["stronghold"] = {
                "enabled": True,
                "nearest_enabled": stmt.nearest_max_dist is not None,
                "nearest_dist": str(stmt.nearest_max_dist or 1500),
                "nearest_ref": ref,
                "nearest_ref_pos": ref_pos,
                "under_spawn": stmt.under_player,
                "full": stmt.full,
                "ring": stmt.ring,
                "max_angle": stmt.max_angle_deg,
            }
        elif isinstance(stmt, StructureRule):
            if stmt.structure in ("ruined_portal", "ruined_portal_n"):
                return
            features.add("structures")
            ref, ref_pos = _ref_to_gui(stmt.ref, stmt.ref_pos)
            structures.append(
                {
                    "enabled": True,
                    "name": stmt.structure,
                    "dimension": dimension,
                    "ref": ref,
                    "ref_pos": ref_pos,
                    "max_dist": str(stmt.max_dist),
                    "viable": stmt.viable,
                    "abandoned": (
                        "true" if stmt.village_abandoned else "false"
                    )
                    if stmt.structure == "village" and stmt.village_abandoned is not None
                    else None,
                }
            )
        elif isinstance(stmt, RuinedPortalRule):
            features.add("structures")
            ref, ref_pos = _ref_to_gui(stmt.ref, stmt.ref_pos)
            criteria["ruined_portal"] = {
                "enabled": True,
                "dimension": dimension,
                "ref": ref,
                "ref_pos": ref_pos,
                "max_dist": str(stmt.max_dist),
                "viable": stmt.viable,
                "giant": stmt.giant,
                "template": stmt.template,
                "underground": stmt.underground,
                "airpocket": stmt.airpocket,
                "top_missing": str(stmt.top_missing) if stmt.top_missing is not None else "",
                "frame_missing": str(stmt.frame_missing) if stmt.frame_missing is not None else "",
                "chest_items": list(stmt.chest_items),
            }
        elif isinstance(stmt, BastionRule):
            features.add("structures")
            ref, ref_pos = _ref_to_gui(stmt.ref, stmt.ref_pos)
            criteria["bastion"] = {
                "enabled": True,
                "variant": stmt.variant,
                "ref": ref,
                "ref_pos": ref_pos,
                "max_dist": str(stmt.max_dist),
                "viable": stmt.viable,
            }
        elif isinstance(stmt, BiomeAt):
            features.add("biomes")
            criteria["biomes"].append(
                {
                    "enabled": True,
                    "dimension": dimension,
                    "x": str(stmt.x),
                    "y": str(stmt.y),
                    "z": str(stmt.z),
                    "names": _biomes_to_str(stmt.biomes),
                    "negate": stmt.negate,
                }
            )
        elif isinstance(stmt, BiomeRegion):
            features.add("biomes")
            pct = f"{stmt.percent}" if stmt.percent is not None else ""
            criteria["biome_regions"].append(
                {
                    "enabled": True,
                    "dimension": dimension,
                    "x1": str(stmt.x1),
                    "z1": str(stmt.z1),
                    "x2": str(stmt.x2),
                    "z2": str(stmt.z2),
                    "y": str(stmt.y),
                    "op": stmt.op,
                    "biome": stmt.biome,
                    "percent": pct,
                }
            )
        elif isinstance(stmt, TerrainRule):
            features.add("terrain")
            criteria["terrain"].append(
                {
                    "enabled": True,
                    "dimension": dimension,
                    "x": str(stmt.x),
                    "z": str(stmt.z),
                    "radius": str(stmt.radius),
                    "predicate": stmt.predicate,
                    "negate": stmt.negate,
                }
            )
        elif isinstance(stmt, HeightRule):
            features.add("terrain")
            criteria["heights"].append(
                {
                    "enabled": True,
                    "dimension": dimension,
                    "x": str(stmt.x),
                    "z": str(stmt.z),
                    "op": stmt.op,
                    "value": str(stmt.value),
                }
            )
        elif isinstance(stmt, LootRule):
            struct = stmt.structure.lower()
            if struct in STRUCTURE_LOOT_TABLE and structure_kind(struct) == "loot_chest":
                features.add("structures")
                ref, ref_pos = _ref_to_gui(stmt.ref, stmt.ref_pos)
                existing = next(
                    (s for s in structures if s["name"] == struct),
                    None,
                )
                if existing is None:
                    structures.append(
                        {
                            "enabled": True,
                            "name": struct,
                            "dimension": stmt.dimension,
                            "ref": ref,
                            "ref_pos": ref_pos,
                            "max_dist": str(stmt.max_dist),
                            "viable": True,
                            "chest_items": [(stmt.item, stmt.min_count)],
                        }
                    )
                else:
                    existing.setdefault("chest_items", []).append((stmt.item, stmt.min_count))
            else:
                features.add("loot")
                ref, ref_pos = _ref_to_gui(stmt.ref, stmt.ref_pos)
                criteria["loot"].append(
                    {
                        "enabled": True,
                        "structure": stmt.structure,
                        "loot_table": stmt.loot_table or "ruined_portal",
                        "item": stmt.item,
                        "min_count": str(stmt.min_count),
                        "dimension": stmt.dimension,
                        "ref": ref,
                        "ref_pos": ref_pos,
                        "max_dist": str(stmt.max_dist),
                    }
                )
        elif isinstance(stmt, MobRule):
            features.add("loot")
            ref, ref_pos = _ref_to_gui(stmt.ref, stmt.ref_pos)
            criteria["mobs"].append(
                {
                    "enabled": True,
                    "mob": stmt.mob,
                    "dimension": stmt.dimension,
                    "ref": ref,
                    "ref_pos": ref_pos,
                    "max_dist": str(stmt.max_dist),
                    "biomes": _biomes_to_str(stmt.biomes),
                }
            )
        elif isinstance(stmt, StructureBetween):
            features.add("structures")
            ref, ref_pos = _ref_to_gui(stmt.ref, stmt.ref_pos)
            criteria["structure_between"] = [
                {
                    "enabled": True,
                    "dimension": dimension,
                    "structure_a": stmt.structure_a,
                    "structure_b": stmt.structure_b,
                    "ref": ref,
                    "ref_pos": ref_pos,
                    "max_dist": str(stmt.max_dist),
                    "viable": stmt.viable,
                }
            ]
        elif isinstance(stmt, DistanceRule):
            features.add("structures")
            criteria["distance_rules"] = [
                {
                    "enabled": True,
                    "dimension": stmt.dimension,
                    "a": stmt.a,
                    "b": stmt.b,
                    "op": stmt.op,
                    "value": str(int(stmt.value)),
                }
            ]

    for stmt in doc.statements:
        if isinstance(stmt, DimensionBlock):
            for inner in stmt.statements:
                handle(inner, stmt.dimension)
        else:
            handle(stmt)

    criteria["structures"] = structures
    return criteria, features


def parse_ezsf_to_criteria(text: str) -> tuple[dict[str, Any], set[str], Document]:
    doc = parse_ezsf(text)
    criteria, features = document_to_criteria(doc)
    return criteria, features, doc


def _set_chest_rows(app: Any, struct_name: str, items: list[tuple[str, int]]) -> None:
    for row in list(app._chest_rows.get(struct_name, [])):
        row["row"].destroy()
    app._chest_rows[struct_name] = []
    for item, count in items:
        app._add_chest_row(struct_name, item, str(count))
    if not items and struct_name in app._struct_configs:
        app._add_chest_row(struct_name)


def apply_criteria_to_gui(app: Any, criteria: dict[str, Any], features: set[str]) -> None:
    for key in FEATURE_KEYS:
        app._feature_vars[key].set(key in features)

    if doc_version := criteria.get("version"):
        app.version_var.set(doc_version)

    app.threads_var.set(criteria.get("threads", "") or app.threads_var.get())
    app.max_results_var.set(criteria.get("max_results", "") or app.max_results_var.get())
    app.random_var.set(criteria.get("random_search", True))
    app.seed_start_var.set(criteria.get("seed_start") or "")
    app.seed_end_var.set(criteria.get("seed_end") or "")

    for name in app._struct_enabled:
        app._struct_enabled[name].set(False)

    for struct in criteria.get("structures") or []:
        name = struct["name"]
        if name not in app._struct_configs:
            continue
        app._struct_enabled[name].set(True)
        cfg = app._struct_configs[name]
        set_ref(cfg["ref"], struct["ref"], struct.get("ref_pos"))
        cfg["max_dist"].set(struct.get("max_dist", "0"))
        cfg["viable"].set(struct.get("viable", True))
        if name == "village" and "abandoned" in cfg and struct.get("abandoned"):
            cfg["abandoned"].set(str(struct["abandoned"]))
        if struct.get("chest_items"):
            _set_chest_rows(app, name, struct["chest_items"])

    portal = criteria.get("ruined_portal") or {}
    if portal.get("enabled"):
        name = "ruined_portal"
        app._struct_enabled[name].set(True)
        cfg = app._struct_configs[name]
        cfg["dimension_var"].set(portal.get("dimension", "overworld"))
        set_ref(cfg["ref"], portal.get("ref", "spawn"), portal.get("ref_pos"))
        cfg["max_dist"].set(portal.get("max_dist", "500"))
        cfg["viable"].set(portal.get("viable", True))
        cfg["giant"].set(
            "" if portal.get("giant") is None else ("true" if portal["giant"] else "false")
        )
        cfg["template"].set(
            "" if portal.get("template") is None else str(portal["template"])
        )
        cfg["underground"].set(
            ""
            if portal.get("underground") is None
            else ("true" if portal["underground"] else "false")
        )
        cfg["airpocket"].set(
            ""
            if portal.get("airpocket") is None
            else ("true" if portal["airpocket"] else "false")
        )
        cfg["top_missing"].set(portal.get("top_missing", ""))
        cfg["frame_missing"].set(portal.get("frame_missing", ""))
        _set_chest_rows(app, name, portal.get("chest_items") or [])

    bastion = criteria.get("bastion") or {}
    if bastion.get("enabled"):
        name = "bastion"
        app._struct_enabled[name].set(True)
        cfg = app._struct_configs[name]
        cfg["variant"].set(bastion.get("variant", "treasure"))
        set_ref(cfg["ref"], bastion.get("ref", "0,0"), bastion.get("ref_pos"))
        cfg["max_dist"].set(bastion.get("max_dist", "600"))
        cfg["viable"].set(bastion.get("viable", True))

    spawn = criteria.get("spawn") or {}
    app.spawn_require_dist.set(spawn.get("enabled", False))
    set_ref(app.spawn_ref, spawn.get("ref", "origin"), spawn.get("ref_pos"))
    app.spawn_max_dist.set(spawn.get("max_dist", "0"))
    app.spawn_biomes.set(spawn.get("biomes", ""))

    sh = criteria.get("stronghold") or {}
    app.stronghold_require.set(sh.get("enabled", False))
    app.sh_nearest_enabled.set(sh.get("nearest_enabled", False))
    set_ref(app.sh_nearest_ref, sh.get("nearest_ref", "spawn"), sh.get("nearest_ref_pos"))
    app.sh_nearest_dist.set(sh.get("nearest_dist", "1500"))
    app.sh_under_spawn.set(sh.get("under_spawn", False))
    app.sh_full.set(sh.get("full", False))
    if sh.get("ring") is not None:
        app.sh_ring_enabled.set(True)
        app.sh_ring.set(str(sh["ring"]))
    else:
        app.sh_ring_enabled.set(False)
    if sh.get("max_angle") not in (None, ""):
        app.sh_max_angle_enabled.set(True)
        app.sh_max_angle.set(str(sh["max_angle"]))
    else:
        app.sh_max_angle_enabled.set(False)

    biomes = criteria.get("biomes") or []
    if biomes:
        b = biomes[0]
        app.biome_at_require.set(True)
        app.biome_at_dim.set(b.get("dimension", "overworld"))
        app.biome_at_x.set(b.get("x", "0"))
        app.biome_at_y.set(b.get("y", "64"))
        app.biome_at_z.set(b.get("z", "0"))
        app.biome_at_names.set(b.get("names", ""))
        app.biome_at_negate.set(b.get("negate", False))
    else:
        app.biome_at_require.set(False)

    regions = criteria.get("biome_regions") or []
    if regions:
        r = regions[0]
        app.biome_region_require.set(True)
        app.biome_region_dim.set(r.get("dimension", "overworld"))
        app.biome_region_x1.set(r.get("x1", "-512"))
        app.biome_region_z1.set(r.get("z1", "-512"))
        app.biome_region_x2.set(r.get("x2", "512"))
        app.biome_region_z2.set(r.get("z2", "512"))
        app.biome_region_y.set(r.get("y", "64"))
        app.biome_region_op.set(r.get("op", ">="))
        app.biome_region_biome.set(r.get("biome", "desert"))
        app.biome_region_pct.set(r.get("percent", "10"))
    else:
        app.biome_region_require.set(False)

    terrains = criteria.get("terrain") or []
    if terrains:
        t = terrains[0]
        app.terrain_require.set(True)
        app.terrain_dim.set(t.get("dimension", "overworld"))
        app.terrain_x.set(t.get("x", "0"))
        app.terrain_z.set(t.get("z", "0"))
        app.terrain_radius.set(t.get("radius", "128"))
        app.terrain_pred.set(t.get("predicate", "flat"))
        app.terrain_negate.set(t.get("negate", False))
    else:
        app.terrain_require.set(False)

    heights = criteria.get("heights") or []
    if heights:
        h = heights[0]
        app.height_require.set(True)
        app.height_dim.set(h.get("dimension", "overworld"))
        app.height_x.set(h.get("x", "0"))
        app.height_z.set(h.get("z", "0"))
        app.height_op.set(h.get("op", ">="))
        app.height_value.set(h.get("value", "64"))
    else:
        app.height_require.set(False)

    mobs = criteria.get("mobs") or []
    if mobs:
        mob = mobs[0]
        app.mob_type.set(mob.get("mob", "witch"))
        app.mob_dim.set(mob.get("dimension", "overworld"))
        set_ref(app.mob_ref, mob.get("ref", "spawn"), mob.get("ref_pos"))
        app.mob_dist.set(mob.get("max_dist", "200"))
        app.mob_biomes.set(mob.get("biomes", ""))

    between = (criteria.get("structure_between") or [{}])[0]
    app.struct_between_enabled.set(between.get("enabled", False))
    if between.get("enabled"):
        app.struct_between_a.set(between.get("structure_a", "village"))
        app.struct_between_b.set(between.get("structure_b", "ruined_portal"))
        app.struct_between_dim.set(between.get("dimension", "overworld"))
        set_ref(app.struct_between_ref, between.get("ref", "spawn"), between.get("ref_pos"))
        app.struct_between_dist.set(between.get("max_dist", "800"))

    dist_rules = criteria.get("distance_rules") or []
    if dist_rules:
        dr = dist_rules[0]
        app.dist_rule_enabled.set(True)
        app.dist_rule_a.set(dr.get("a", "village"))
        app.dist_rule_b.set(dr.get("b", "ruined_portal"))
        app.dist_rule_op.set(dr.get("op", "<="))
        app.dist_rule_value.set(dr.get("value", "200"))
        app.dist_rule_dim.set(dr.get("dimension", "overworld"))
    else:
        app.dist_rule_enabled.set(False)

    app._refresh_tabs()
