"""Build .ezsf text from GUI criteria selections."""

from __future__ import annotations

from typing import Any


def _ref_line(ref: str, pos: tuple[int, int] | None) -> str:
    if pos is not None:
        return f"{pos[0]},{pos[1]}"
    return ref or "spawn"


def _bool_token(val: Any) -> str | None:
    if val is None or val == "":
        return None
    if isinstance(val, bool):
        return "true" if val else "false"
    s = str(val).lower()
    if s in ("true", "yes", "1", "on"):
        return "true"
    if s in ("false", "no", "0", "off"):
        return "false"
    return None


def _int_or_none(val: Any) -> int | None:
    if val is None or val == "":
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def build_ezsf(criteria: dict[str, Any], version: str = "1.16.1") -> str:
    lines: list[str] = []

    if criteria.get("emit_version", True):
        lines.append(f"version {version}")

    threads = _int_or_none(criteria.get("threads"))
    if threads:
        lines.append(f"threads {threads}")
    max_results = _int_or_none(criteria.get("max_results"))
    if max_results:
        lines.append(f"max_results {max_results}")

    seed_start = criteria.get("seed_start")
    seed_end = criteria.get("seed_end")
    if seed_start not in (None, "") and seed_end not in (None, ""):
        lines.append(f"seed {seed_start} to {seed_end}")

    if criteria.get("random_search") is False:
        lines.append("sequential")

    spawn = criteria.get("spawn") or {}
    if spawn.get("enabled"):
        ref = _ref_line(spawn.get("ref", "origin"), spawn.get("ref_pos"))
        dist = _int_or_none(spawn.get("max_dist"))
        if dist and dist > 0:
            lines.append(f"spawn within {dist} of {ref}")
        biomes = (spawn.get("biomes") or "").strip()
        if biomes:
            lines.append(f"spawn biome {biomes}")

    stronghold = criteria.get("stronghold") or {}
    if stronghold.get("enabled"):
        parts: list[str] = ["stronghold"]
        if stronghold.get("nearest_enabled"):
            dist = _int_or_none(stronghold.get("nearest_dist"))
            ref = _ref_line(stronghold.get("nearest_ref", "spawn"), stronghold.get("nearest_ref_pos"))
            if dist:
                parts += ["nearest", f"within {dist}", "of", ref]
        if stronghold.get("under_spawn"):
            parts += ["under", "spawn"]
        if stronghold.get("full"):
            parts.append("full")
        ring = _int_or_none(stronghold.get("ring"))
        if ring is not None:
            parts += ["ring", str(ring)]
        if len(parts) > 1:
            lines.append(" ".join(parts))

    overworld: list[str] = []
    nether: list[str] = []
    end: list[str] = []

    for struct in criteria.get("structures") or []:
        if not struct.get("enabled"):
            continue
        dim = struct.get("dimension", "overworld")
        name = struct["name"]
        dist = _int_or_none(struct.get("max_dist"))
        if not dist:
            continue
        ref = _ref_line(struct.get("ref", "spawn"), struct.get("ref_pos"))
        line = f"structure {name} within {dist} of {ref}"
        if struct.get("viable", True):
            line += " viable"
        if struct.get("not_viable"):
            line = line.replace(" viable", " not viable")
        target = overworld if dim == "overworld" else nether if dim == "nether" else end
        target.append(line)

    portal = criteria.get("ruined_portal") or {}
    if portal.get("enabled"):
        dist = _int_or_none(portal.get("max_dist")) or 500
        ref = _ref_line(portal.get("ref", "spawn"), portal.get("ref_pos"))
        dim = portal.get("dimension", "overworld")
        parts = [f"ruined_portal within {dist} of {ref}"]
        if portal.get("viable", True):
            parts.append("viable")
        giant = _bool_token(portal.get("giant"))
        if giant:
            parts += ["giant", giant]
        underground = _bool_token(portal.get("underground"))
        if underground:
            parts += ["underground", underground]
        airpocket = _bool_token(portal.get("airpocket"))
        if airpocket:
            parts += ["airpocket", airpocket]
        template = _int_or_none(portal.get("template"))
        if template is not None:
            parts += ["template", str(template)]
        top_missing = _int_or_none(portal.get("top_missing"))
        if top_missing is not None:
            parts += ["top_missing", str(top_missing)]
        frame_missing = _int_or_none(portal.get("frame_missing"))
        if frame_missing is not None:
            parts += ["frame_missing", str(frame_missing)]
        for item, count in portal.get("chest_items") or []:
            item = str(item).strip()
            count = _int_or_none(count) or 1
            if item:
                parts += ["chest", "item", item, "min", str(count)]
        line = " ".join(parts)
        target = overworld if dim == "overworld" else nether
        target.append(line)

    bastion = criteria.get("bastion") or {}
    if bastion.get("enabled"):
        dist = _int_or_none(bastion.get("max_dist")) or 600
        ref = _ref_line(bastion.get("ref", "0,0"), bastion.get("ref_pos"))
        variant = (bastion.get("variant") or "treasure").strip()
        line = f"bastion variant {variant} within {dist} of {ref}"
        if bastion.get("viable", True):
            line += " viable"
        nether.append(line)

    for biome in criteria.get("biomes") or []:
        if not biome.get("enabled"):
            continue
        dim = biome.get("dimension", "overworld")
        x = _int_or_none(biome.get("x")) or 0
        y = _int_or_none(biome.get("y")) or 64
        z = _int_or_none(biome.get("z")) or 0
        names = (biome.get("names") or "").strip()
        if not names:
            continue
        prefix = "not " if biome.get("negate") else ""
        line = f"biome at {x}, {y}, {z} {prefix}{names}"
        target = overworld if dim == "overworld" else nether if dim == "nether" else end
        target.append(line)

    for region in criteria.get("biome_regions") or []:
        if not region.get("enabled"):
            continue
        dim = region.get("dimension", "overworld")
        x1 = _int_or_none(region.get("x1")) or -512
        z1 = _int_or_none(region.get("z1")) or -512
        x2 = _int_or_none(region.get("x2")) or 512
        z2 = _int_or_none(region.get("z2")) or 512
        y = _int_or_none(region.get("y")) or 64
        biome = (region.get("biome") or "").strip()
        op = region.get("op", ">=")
        pct = region.get("percent")
        if not biome:
            continue
        line = f"biome region {x1}, {z1} to {x2}, {z2} y {y} {op} {biome}"
        if pct not in (None, ""):
            line += f" {pct}%"
        target = overworld if dim == "overworld" else nether if dim == "nether" else end
        target.append(line)

    for terrain in criteria.get("terrain") or []:
        if not terrain.get("enabled"):
            continue
        dim = terrain.get("dimension", "overworld")
        x = _int_or_none(terrain.get("x")) or 0
        z = _int_or_none(terrain.get("z")) or 0
        radius = _int_or_none(terrain.get("radius")) or 64
        pred = terrain.get("predicate", "flat")
        prefix = "not " if terrain.get("negate") else ""
        line = f"terrain at {x}, {z} {prefix}{pred} radius {radius}"
        target = overworld if dim == "overworld" else nether if dim == "nether" else end
        target.append(line)

    for height in criteria.get("heights") or []:
        if not height.get("enabled"):
            continue
        dim = height.get("dimension", "overworld")
        x = _int_or_none(height.get("x")) or 0
        z = _int_or_none(height.get("z")) or 0
        op = height.get("op", ">=")
        val = _int_or_none(height.get("value")) or 64
        line = f"height at {x}, {z} {op} {val}"
        target = overworld if dim == "overworld" else nether if dim == "nether" else end
        target.append(line)

    for loot in criteria.get("loot") or []:
        if not loot.get("enabled"):
            continue
        struct = loot.get("structure", "ruined_portal")
        item = (loot.get("item") or "").strip()
        if not item:
            continue
        count = _int_or_none(loot.get("min_count")) or 1
        dim = loot.get("dimension", "overworld")
        dist = _int_or_none(loot.get("max_dist"))
        ref = _ref_line(loot.get("ref", "spawn"), loot.get("ref_pos"))
        line = f"loot at {struct} item {item} min {count}"
        table = (loot.get("loot_table") or "").strip()
        if table:
            line += f" table {table}"
        if dist:
            line += f" within {dist} of {ref}"
        if dim != "overworld":
            line += f" in {dim}"
        lines.append(line)

    for mob in criteria.get("mobs") or []:
        if not mob.get("enabled"):
            continue
        name = (mob.get("mob") or "").strip()
        if not name:
            continue
        dim = mob.get("dimension", "overworld")
        dist = _int_or_none(mob.get("max_dist")) or 500
        ref = _ref_line(mob.get("ref", "spawn"), mob.get("ref_pos"))
        biomes = (mob.get("biomes") or "").strip()
        line = f"mob {name} within {dist} of {ref} in {dim}"
        if biomes:
            line += f" biome {biomes}"
        lines.append(line)

    for between in criteria.get("structure_between") or []:
        if not between.get("enabled"):
            continue
        dim = between.get("dimension", "overworld")
        a = between.get("structure_a", "village")
        b = between.get("structure_b", "ruined_portal")
        dist = _int_or_none(between.get("max_dist")) or 800
        ref = _ref_line(between.get("ref", "spawn"), between.get("ref_pos"))
        line = f"structure between {a} and {b} within {dist} of {ref}"
        if between.get("viable", True):
            line += " viable"
        target = overworld if dim == "overworld" else nether if dim == "nether" else end
        target.append(line)

    for dist_rule in criteria.get("distance_rules") or []:
        if not dist_rule.get("enabled"):
            continue
        dim = dist_rule.get("dimension", "overworld")
        a = dist_rule.get("a", "village")
        b = dist_rule.get("b", "ruined_portal")
        op = dist_rule.get("op", "<=")
        val = dist_rule.get("value", 200)
        line = f"distance {a} {b} {op} {val} in {dim}"
        lines.append(line)

    if overworld:
        lines.append("dimension overworld {")
        lines.extend(f"  {l}" for l in overworld)
        lines.append("}")
    if nether:
        lines.append("dimension nether {")
        lines.extend(f"  {l}" for l in nether)
        lines.append("}")
    if end:
        lines.append("dimension end {")
        lines.extend(f"  {l}" for l in end)
        lines.append("}")

    return "\n".join(lines).strip()
