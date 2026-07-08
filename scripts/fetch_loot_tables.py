#!/usr/bin/env python3
"""Download vanilla loot tables from misode/mcmeta and write ezseedfinder loot_data JSON."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import importlib.util


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_engine = ROOT / "ezseedfinder" / "engine"
_load_module("ezseedfinder.engine.java_random", _engine / "java_random.py")
loot_tables = _load_module("ezseedfinder.engine.loot_tables", _engine / "loot_tables.py")

MCMETA_VERSION_TAGS = loot_tables.MCMETA_VERSION_TAGS
VANILLA_TABLE_FILES = loot_tables.VANILLA_TABLE_FILES
parse_vanilla_loot_table = loot_tables.parse_vanilla_loot_table
write_version_loot_file = loot_tables.write_version_loot_file

MCMETA_BASE = "https://raw.githubusercontent.com/misode/mcmeta/{tag}-data-json/data/minecraft"


def _loot_paths_for_tag(tag: str) -> tuple[str, ...]:
    # 1.16 uses loot_tables/; modern uses loot_table/
    if _parse_version_tuple(tag) < (1, 17):
        return ("loot_tables", "loot_table")
    return ("loot_table", "loot_tables")


def _parse_version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in version.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        if digits:
            parts.append(int(digits))
    return tuple(parts) if parts else (0,)


def fetch_vanilla_table(tag: str, rel_path: str) -> dict | None:
    for root in _loot_paths_for_tag(tag):
        url = f"{MCMETA_BASE.format(tag=tag)}/{root}/{rel_path}"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError:
            continue
    return None


def fetch_version(version: str) -> dict:
    tag = MCMETA_VERSION_TAGS.get(version, version)
    tables = {}
    for our_name, rel_path in VANILLA_TABLE_FILES.items():
        raw = fetch_vanilla_table(tag, rel_path)
        if raw is None:
            print(f"  skip {our_name} (not in {tag})")
            continue
        tables[our_name] = parse_vanilla_loot_table(raw)
        print(f"  ok   {our_name}")
    return tables


def main() -> int:
    versions = sys.argv[1:] or sorted(set(MCMETA_VERSION_TAGS.values()))
    for version in versions:
        print(f"Fetching {version}...")
        tables = fetch_version(version)
        if not tables:
            print(f"  no tables for {version}")
            continue
        path = write_version_loot_file(version, tables)
        print(f"  wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
