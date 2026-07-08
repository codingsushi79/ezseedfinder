"""Tests that do not require the cubiomes native library."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_engine_module(name: str, filename: str):
    path = ROOT / "ezseedfinder" / "engine" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_load_engine_module("ezseedfinder.engine.java_random", "java_random.py")
loot_tables = _load_engine_module("ezseedfinder.engine.loot_tables", "loot_tables.py")

from ezseedfinder.ezsf.parser import parse_ezsf  # noqa: E402


def test_loot_version_lodestone():
    items_116 = loot_tables.loot_table_item_names("1.16.1", "ruined_portal")
    items_262 = loot_tables.loot_table_item_names("26.1.2", "ruined_portal")
    assert "lodestone" not in items_116
    assert "lodestone" in items_262


def test_loot_roll_differs_by_version():
    seed, x, y, z = 42, 10, 64, 20
    r1 = loot_tables.roll_chest_loot("ruined_portal", "1.16.1", seed, x, y, z)
    r2 = loot_tables.roll_chest_loot("ruined_portal", "26.1.2", seed, x, y, z)
    assert r1.items != r2.items or "lodestone" in r2.items


def test_parser_stronghold_max_angle():
    doc = parse_ezsf("stronghold nearest within 1200 of spawn max_angle 45")
    assert len(doc.statements) == 1
    rule = doc.statements[0]
    assert rule.max_angle_deg == 45.0


def test_parser_village_abandoned():
    doc = parse_ezsf(
        "dimension overworld {\n"
        "  structure village within 500 of spawn viable abandoned false\n"
        "}"
    )
    block = doc.statements[0]
    rule = block.statements[0]
    assert rule.village_abandoned is False


def test_parser_roundtrip_structure_between():
    text = (
        "dimension overworld {\n"
        "  structure between village and ruined_portal within 200 of spawn viable\n"
        "}"
    )
    doc = parse_ezsf(text)
    stmt = doc.statements[0].statements[0]
    assert stmt.structure_a == "village"
    assert stmt.structure_b == "ruined_portal"
