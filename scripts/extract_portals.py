#!/usr/bin/env python3
"""Extract ruined portal template metadata from a 1.16.1 client jar."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

from nbtlib import File


def frame_coords(ox: int, oy: int, oz: int, axis: str, width: int, height: int) -> list[tuple[int, int, int]]:
    w, h = width, height
    if axis == "z":
        return [
            (ox + x, oy + y, oz)
            for x in range(w)
            for y in range(h)
            if x in (0, w - 1) or y in (0, h - 1)
        ]
    if axis == "x":
        return [
            (ox, oy + y, oz + z)
            for z in range(w)
            for y in range(h)
            if z in (0, w - 1) or y in (0, h - 1)
        ]
    return [
        (ox + x, oy, oz + z)
        for x in range(w)
        for z in range(w)
        if x in (0, w - 1) or z in (0, w - 1)
    ]


def top_coords(ox: int, oy: int, oz: int, axis: str, width: int, height: int) -> list[tuple[int, int, int]]:
    top_y = height - 1
    if axis == "z":
        return [(ox + x, oy + top_y, oz) for x in range(width)]
    if axis == "x":
        return [(ox, oy + top_y, oz + z) for z in range(width)]
    top_z = width - 1
    return [(ox + x, oy, oz + top_z) for x in range(width)]


def find_best_frame(obs: list[tuple[int, int, int]]) -> dict | None:
    obs_set = set(obs)
    best = None
    for width, height in ((4, 5), (5, 5)):
        for axis in ("z", "x", "y"):
            for ox in range(-10, 15):
                for oy in range(-10, 15):
                    for oz in range(-10, 15):
                        frame = set(frame_coords(ox, oy, oz, axis, width, height))
                        present = frame & obs_set
                        if len(present) < width + height:
                            continue
                        missing = frame - obs_set
                        top = set(top_coords(ox, oy, oz, axis, width, height))
                        top_miss = top - obs_set
                        non_top_miss = missing - top
                        # Prefer complete frames with holes only on the top row
                        score = len(present) * 100 - len(missing) * 10
                        if not non_top_miss:
                            score += 500
                        if len(top_miss) == 1 and not non_top_miss:
                            score += 200
                        entry = {
                            "score": score,
                            "width": width,
                            "height": height,
                            "axis": axis,
                            "origin": [ox, oy, oz],
                            "present": len(present),
                            "missing": len(missing),
                            "top_missing": len(top_miss),
                            "non_top_missing": len(non_top_miss),
                            "top_missing_pos": [list(p) for p in sorted(top_miss)],
                            "missing_pos": [list(p) for p in sorted(missing)],
                            "frame_coords": [list(p) for p in sorted(frame)],
                        }
                        if best is None or entry["score"] > best["score"]:
                            best = entry
    return best


def main() -> None:
    jar = sys.argv[1] if len(sys.argv) > 1 else "/tmp/client_1.16.1.jar"
    out = Path(__file__).resolve().parents[1] / "ezseedfinder/engine/portal_templates_data.json"
    templates: dict = {}

    with zipfile.ZipFile(jar) as zf:
        names = [n for n in zf.namelist() if n.startswith("data/minecraft/structures/ruined_portal/")]
        for name in sorted(names):
            if not name.endswith(".nbt"):
                continue
            key = Path(name).stem
            data = zf.read(name)
            tmp = Path("/tmp") / f"{key}.nbt"
            tmp.write_bytes(data)
            f = File.load(str(tmp), gzipped=True)
            palette = [str(p["Name"]) for p in f["palette"]]
            obs = [
                tuple(int(v) for v in b["pos"])
                for b in f["blocks"]
                if palette[b["state"]] == "minecraft:obsidian"
            ]
            chest = next(
                (
                    tuple(int(v) for v in b["pos"])
                    for b in f["blocks"]
                    if palette[b["state"]] == "minecraft:chest"
                ),
                None,
            )
            frame = find_best_frame(obs)
            templates[key] = {
                "obsidian": [list(p) for p in obs],
                "chest": list(chest) if chest else None,
                "frame": frame,
            }
            if frame:
                print(
                    f"{key}: {frame['width']}x{frame['height']} present={frame['present']} "
                    f"missing={frame['missing']} top_miss={frame['top_missing']} "
                    f"non_top_miss={frame['non_top_missing']}"
                )

    out.write_text(json.dumps(templates, indent=2))
    print("wrote", out)


if __name__ == "__main__":
    main()
