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
from .criteria_widgets import resolve_ref, set_ref
from .structure_registry import STRUCTURE_LOOT_TABLE, structure_kind


FEATURE_KEYS = ("structures", "spawn", "biomes", "terrain", "loot")


def _set_if_changed(var: Any, value: Any) -> bool:
    if isinstance(value, bool):
        if bool(var.get()) == value:
            return False
    elif str(var.get()) == str(value):
        return False
    var.set(value)
    return True


def _set_ref_if_changed(data: dict[str, Any], ref: str, ref_pos: tuple[int, int] | None) -> bool:
    cur_ref, cur_pos = resolve_ref(data)
    if cur_ref == ref and cur_pos == ref_pos:
        return False
    set_ref(data, ref, ref_pos)
    return True


def _target_enabled_structures(criteria: dict[str, Any]) -> set[str]:
    names = {struct["name"] for struct in criteria.get("structures") or []}
    if (criteria.get("ruined_portal") or {}).get("enabled"):
        names.add("ruined_portal")
    if (criteria.get("bastion") or {}).get("enabled"):
        names.add("bastion")
    return names


def _set_chest_rows_if_changed(
    app: Any,
    struct_name: str,
    items: list[tuple[str, int]],
) -> None:
    if struct_name not in app._struct_configs:
        return
    existing: list[tuple[str, int]] = []
    for row in app._chest_rows.get(struct_name, []):
        item = row["item"].get().strip()
        if not item:
            continue
        try:
            count = int(row["count"].get())
        except ValueError:
            count = 1
        existing.append((item, count))
    normalized = [(item, int(count)) for item, count in items]
    if existing == normalized:
        return
    _set_chest_rows(app, struct_name, items)


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
    tabs_dirty = False

    for key in FEATURE_KEYS:
        if _set_if_changed(app._feature_vars[key], key in features):
            tabs_dirty = True

    if doc_version := criteria.get("version"):
        _set_if_changed(app.version_var, doc_version)

    _set_if_changed(app.threads_var, criteria.get("threads", "") or app.threads_var.get())
    _set_if_changed(app.max_results_var, criteria.get("max_results", "") or app.max_results_var.get())
    _set_if_changed(app.random_var, criteria.get("random_search", True))
    _set_if_changed(app.seed_start_var, criteria.get("seed_start") or "")
    _set_if_changed(app.seed_end_var, criteria.get("seed_end") or "")

    target_structs = _target_enabled_structures(criteria)
    for name, var in app._struct_enabled.items():
        want = name in target_structs
        if var.get() != want:
            if want:
                app._ensure_struct_tab(name)
            var.set(want)
            tabs_dirty = True

    for struct in criteria.get("structures") or []:
        name = struct["name"]
        if name not in app._struct_configs:
            continue
        cfg = app._struct_configs[name]
        _set_ref_if_changed(cfg["ref"], struct["ref"], struct.get("ref_pos"))
        _set_if_changed(cfg["max_dist"], struct.get("max_dist", "0"))
        _set_if_changed(cfg["viable"], struct.get("viable", True))
        if name == "village" and "abandoned" in cfg and struct.get("abandoned"):
            _set_if_changed(cfg["abandoned"], str(struct["abandoned"]))
        if struct.get("chest_items"):
            _set_chest_rows_if_changed(app, name, struct["chest_items"])

    portal = criteria.get("ruined_portal") or {}
    if portal.get("enabled"):
        name = "ruined_portal"
        if name in app._struct_configs:
            cfg = app._struct_configs[name]
            _set_if_changed(cfg["dimension_var"], portal.get("dimension", "overworld"))
            _set_ref_if_changed(cfg["ref"], portal.get("ref", "spawn"), portal.get("ref_pos"))
            _set_if_changed(cfg["max_dist"], portal.get("max_dist", "500"))
            _set_if_changed(cfg["viable"], portal.get("viable", True))
            _set_if_changed(
                cfg["giant"],
                "" if portal.get("giant") is None else ("true" if portal["giant"] else "false"),
            )
            _set_if_changed(
                cfg["template"],
                "" if portal.get("template") is None else str(portal["template"]),
            )
            _set_if_changed(
                cfg["underground"],
                ""
                if portal.get("underground") is None
                else ("true" if portal["underground"] else "false"),
            )
            _set_if_changed(
                cfg["airpocket"],
                ""
                if portal.get("airpocket") is None
                else ("true" if portal["airpocket"] else "false"),
            )
            _set_if_changed(cfg["top_missing"], portal.get("top_missing", ""))
            _set_if_changed(cfg["frame_missing"], portal.get("frame_missing", ""))
            _set_chest_rows_if_changed(app, name, portal.get("chest_items") or [])

    bastion = criteria.get("bastion") or {}
    if bastion.get("enabled") and "bastion" in app._struct_configs:
        cfg = app._struct_configs["bastion"]
        _set_if_changed(cfg["variant"], bastion.get("variant", "treasure"))
        _set_ref_if_changed(cfg["ref"], bastion.get("ref", "0,0"), bastion.get("ref_pos"))
        _set_if_changed(cfg["max_dist"], bastion.get("max_dist", "600"))
        _set_if_changed(cfg["viable"], bastion.get("viable", True))

    if "spawn" in features or (criteria.get("spawn") or {}).get("enabled"):
        app._ensure_feature_tab("spawn")
    spawn = criteria.get("spawn") or {}
    if hasattr(app, "spawn_require_dist"):
        _set_if_changed(app.spawn_require_dist, spawn.get("enabled", False))
        _set_ref_if_changed(app.spawn_ref, spawn.get("ref", "origin"), spawn.get("ref_pos"))
        _set_if_changed(app.spawn_max_dist, spawn.get("max_dist", "0"))
        _set_if_changed(app.spawn_biomes, spawn.get("biomes", ""))

    sh = criteria.get("stronghold") or {}
    if "spawn" in features or sh.get("enabled") or sh.get("nearest_enabled") or sh.get("under_spawn") or sh.get("full") or sh.get("ring") is not None:
        app._ensure_feature_tab("spawn")
    if hasattr(app, "stronghold_require"):
        _set_if_changed(app.stronghold_require, sh.get("enabled", False))
        _set_if_changed(app.sh_nearest_enabled, sh.get("nearest_enabled", False))
        _set_ref_if_changed(app.sh_nearest_ref, sh.get("nearest_ref", "spawn"), sh.get("nearest_ref_pos"))
        _set_if_changed(app.sh_nearest_dist, sh.get("nearest_dist", "1500"))
        _set_if_changed(app.sh_under_spawn, sh.get("under_spawn", False))
        _set_if_changed(app.sh_full, sh.get("full", False))
        if sh.get("ring") is not None:
            _set_if_changed(app.sh_ring_enabled, True)
            _set_if_changed(app.sh_ring, str(sh["ring"]))
        elif app.sh_ring_enabled.get():
            _set_if_changed(app.sh_ring_enabled, False)
        if sh.get("max_angle") not in (None, ""):
            _set_if_changed(app.sh_max_angle_enabled, True)
            _set_if_changed(app.sh_max_angle, str(sh["max_angle"]))
        elif app.sh_max_angle_enabled.get():
            _set_if_changed(app.sh_max_angle_enabled, False)

    biomes = criteria.get("biomes") or []
    regions = criteria.get("biome_regions") or []
    if "biomes" in features or biomes or regions:
        app._ensure_feature_tab("biomes")
    if hasattr(app, "biome_at_require"):
        if biomes:
            b = biomes[0]
            _set_if_changed(app.biome_at_require, True)
            _set_if_changed(app.biome_at_dim, b.get("dimension", "overworld"))
            _set_if_changed(app.biome_at_x, b.get("x", "0"))
            _set_if_changed(app.biome_at_y, b.get("y", "64"))
            _set_if_changed(app.biome_at_z, b.get("z", "0"))
            _set_if_changed(app.biome_at_names, b.get("names", ""))
            _set_if_changed(app.biome_at_negate, b.get("negate", False))
        elif app.biome_at_require.get():
            _set_if_changed(app.biome_at_require, False)

    if hasattr(app, "biome_region_require"):
        if regions:
            r = regions[0]
            _set_if_changed(app.biome_region_require, True)
            _set_if_changed(app.biome_region_dim, r.get("dimension", "overworld"))
            _set_if_changed(app.biome_region_x1, r.get("x1", "-512"))
            _set_if_changed(app.biome_region_z1, r.get("z1", "-512"))
            _set_if_changed(app.biome_region_x2, r.get("x2", "512"))
            _set_if_changed(app.biome_region_z2, r.get("z2", "512"))
            _set_if_changed(app.biome_region_y, r.get("y", "64"))
            _set_if_changed(app.biome_region_op, r.get("op", ">="))
            _set_if_changed(app.biome_region_biome, r.get("biome", "desert"))
            _set_if_changed(app.biome_region_pct, r.get("percent", "10"))
        elif app.biome_region_require.get():
            _set_if_changed(app.biome_region_require, False)

    terrains = criteria.get("terrain") or []
    heights = criteria.get("heights") or []
    if "terrain" in features or terrains or heights:
        app._ensure_feature_tab("terrain")
    if hasattr(app, "terrain_require"):
        if terrains:
            t = terrains[0]
            _set_if_changed(app.terrain_require, True)
            _set_if_changed(app.terrain_dim, t.get("dimension", "overworld"))
            _set_if_changed(app.terrain_x, t.get("x", "0"))
            _set_if_changed(app.terrain_z, t.get("z", "0"))
            _set_if_changed(app.terrain_radius, t.get("radius", "128"))
            _set_if_changed(app.terrain_pred, t.get("predicate", "flat"))
            _set_if_changed(app.terrain_negate, t.get("negate", False))
        elif app.terrain_require.get():
            _set_if_changed(app.terrain_require, False)

    if hasattr(app, "height_require"):
        if heights:
            h = heights[0]
            _set_if_changed(app.height_require, True)
            _set_if_changed(app.height_dim, h.get("dimension", "overworld"))
            _set_if_changed(app.height_x, h.get("x", "0"))
            _set_if_changed(app.height_z, h.get("z", "0"))
            _set_if_changed(app.height_op, h.get("op", ">="))
            _set_if_changed(app.height_value, h.get("value", "64"))
        elif app.height_require.get():
            _set_if_changed(app.height_require, False)

    mobs = criteria.get("mobs") or []
    if "loot" in features or mobs:
        app._ensure_feature_tab("loot")
    if hasattr(app, "mob_type") and mobs:
        mob = mobs[0]
        _set_if_changed(app.mob_type, mob.get("mob", "witch"))
        _set_if_changed(app.mob_dim, mob.get("dimension", "overworld"))
        _set_ref_if_changed(app.mob_ref, mob.get("ref", "spawn"), mob.get("ref_pos"))
        _set_if_changed(app.mob_dist, mob.get("max_dist", "200"))
        _set_if_changed(app.mob_biomes, mob.get("biomes", ""))

    between = (criteria.get("structure_between") or [{}])[0]
    _set_if_changed(app.struct_between_enabled, between.get("enabled", False))
    if between.get("enabled"):
        _set_if_changed(app.struct_between_a, between.get("structure_a", "village"))
        _set_if_changed(app.struct_between_b, between.get("structure_b", "ruined_portal"))
        _set_if_changed(app.struct_between_dim, between.get("dimension", "overworld"))
        _set_ref_if_changed(app.struct_between_ref, between.get("ref", "spawn"), between.get("ref_pos"))
        _set_if_changed(app.struct_between_dist, between.get("max_dist", "800"))

    dist_rules = criteria.get("distance_rules") or []
    if dist_rules:
        dr = dist_rules[0]
        _set_if_changed(app.dist_rule_enabled, True)
        _set_if_changed(app.dist_rule_a, dr.get("a", "village"))
        _set_if_changed(app.dist_rule_b, dr.get("b", "ruined_portal"))
        _set_if_changed(app.dist_rule_op, dr.get("op", "<="))
        _set_if_changed(app.dist_rule_value, dr.get("value", "200"))
        _set_if_changed(app.dist_rule_dim, dr.get("dimension", "overworld"))
    elif app.dist_rule_enabled.get():
        _set_if_changed(app.dist_rule_enabled, False)

    if tabs_dirty:
        app._refresh_tabs()
