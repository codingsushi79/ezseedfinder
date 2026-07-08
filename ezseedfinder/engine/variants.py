"""Structure variant detection and ruined portal frame analysis."""

from __future__ import annotations

import ctypes
import json
import os
from dataclasses import dataclass
from pathlib import Path

from cubiomespi import Dimension, Generator, Structure

from .java_random import JavaRandom, chunk_generate_rnd, structure_processor_seed
from .loot_tables import LootResult, roll_ruined_portal_chest

_DATA_PATH = Path(__file__).with_name("portal_templates_data.json")
_TEMPLATES: dict | None = None

# cubiomes structure type ids
RUINED_PORTAL = Structure.Ruined_Portal[0]
RUINED_PORTAL_N = Structure.Ruined_Portal_N[0]
BASTION = Structure.Bastion[0]
VILLAGE = Structure.Village[0]


class StructureVariantC(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint8),
        ("size", ctypes.c_uint8),
        ("start", ctypes.c_uint8),
        ("biome", ctypes.c_int16),
        ("rotation", ctypes.c_uint8),
        ("mirror", ctypes.c_uint8),
        ("x", ctypes.c_int16),
        ("y", ctypes.c_int16),
        ("z", ctypes.c_int16),
        ("sx", ctypes.c_int16),
        ("sy", ctypes.c_int16),
        ("sz", ctypes.c_int16),
    ]

    @property
    def abandoned(self) -> bool:
        return bool(self.flags & 1)

    @property
    def giant(self) -> bool:
        return bool(self.flags & 2)

    @property
    def underground(self) -> bool:
        return bool(self.flags & 4)

    @property
    def airpocket(self) -> bool:
        return bool(self.flags & 8)

    @property
    def basement(self) -> bool:
        return bool(self.flags & 16)

    @property
    def cracked(self) -> bool:
        return bool(self.flags & 32)


_lib = None


def _lib_c():
    global _lib
    if _lib is None:
        from cubiomespi._native import load_native_lib

        _lib = load_native_lib()
        _lib.INTERFACE_getVariant.argtypes = [
            ctypes.POINTER(StructureVariantC),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint64,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        _lib.INTERFACE_getVariant.restype = ctypes.c_int
    return _lib


def get_structure_variant(
    struct_id: int, mc_version: int, seed: int, x: int, z: int, biome_id: int = -1
) -> StructureVariantC | None:
    sv = StructureVariantC()
    ok = _lib_c().INTERFACE_getVariant(
        ctypes.byref(sv),
        struct_id,
        mc_version,
        ctypes.c_uint64(seed & ((1 << 64) - 1)),
        x,
        z,
        biome_id,
    )
    return sv if ok else None


def load_templates() -> dict:
    global _TEMPLATES
    if _TEMPLATES is None:
        with open(_DATA_PATH, encoding="utf-8") as f:
            _TEMPLATES = json.load(f)
    return _TEMPLATES


def template_key(giant: bool, start: int) -> str:
    if giant:
        return f"giant_portal_{start}"
    return f"portal_{start}"


def rotate_pos(x: int, y: int, z: int, size: list[int], rotation: int, mirror: bool) -> tuple[int, int, int]:
    sx, sy, sz = size
    if mirror:
        x = sx - 1 - x
    if rotation == 0:
        return x, y, z
    if rotation == 1:
        return sz - 1 - z, y, x
    if rotation == 2:
        return sx - 1 - x, y, sz - 1 - z
    return z, y, sx - 1 - x


# A minimum Nether portal frame (4x5 outer, corners optional) needs 10 obsidian.
MIN_PORTAL_OBSIDIAN = 10


@dataclass
class PortalFrameResult:
    template: str
    giant: bool
    rotation: int
    mirror: bool
    valid_obsidian: int
    frame_missing: int
    top_missing: int
    non_top_missing: int
    crying_count: int
    chest_pos: tuple[int, int, int] | None
    obsidian_total: int = 0
    loot: LootResult | None = None

    def missing_top_only(self, count: int = 1) -> bool:
        return (
            self.top_missing == count
            and self.frame_missing == count
            and self.non_top_missing == 0
        )

    @property
    def usable_obsidian(self) -> int:
        """Number of real (non-crying) obsidian blocks the portal provides."""
        return self.obsidian_total - self.crying_count

    def is_lightable(self, min_obsidian: int = MIN_PORTAL_OBSIDIAN) -> bool:
        """True if the portal has no crying obsidian and enough normal obsidian
        to complete a working Nether portal."""
        return self.crying_count == 0 and self.usable_obsidian >= min_obsidian


def simulate_ruined_portal(
    mc_version: int,
    seed: int,
    x: int,
    z: int,
    biome_id: int,
    game_version: str = "1.16.1",
    surface_y: int | None = None,
    roll_loot: bool = True,
    nether: bool = False,
) -> PortalFrameResult | None:
    struct_id = RUINED_PORTAL_N if nether else RUINED_PORTAL
    sv = get_structure_variant(struct_id, mc_version, seed, x, z, biome_id)
    if sv is None:
        return None

    templates = load_templates()
    key = template_key(sv.giant, sv.start)
    tpl = templates.get(key)
    if not tpl or not tpl.get("frame"):
        return None

    frame_coords = [tuple(p) for p in tpl["frame"]["frame_coords"]]
    obsidian = [tuple(p) for p in tpl["obsidian"]]
    size = [max(p[i] for p in obsidian + frame_coords) + 1 for i in range(3)]

    # Apply rotation/mirror to template-local coords
    local_obs = {rotate_pos(*p, size, sv.rotation, bool(sv.mirror)) for p in obsidian}
    local_frame = [rotate_pos(*p, size, sv.rotation, bool(sv.mirror)) for p in frame_coords]
    frame_y = max(p[1] for p in local_frame)

    place_x, place_z = x, z
    if surface_y is not None:
        place_y = surface_y
    elif sv.y != 0:
        place_y = int(sv.y)
    else:
        place_y = 48 if nether else 64

    # Crying obsidian replacement (15% per obsidian, template block order)
    rng = JavaRandom(structure_processor_seed(seed, place_x, place_y, place_z))
    valid_obs = set()
    crying = 0
    for p in obsidian:
        lp = rotate_pos(*p, size, sv.rotation, bool(sv.mirror))
        if rng.next_float() >= 0.15:
            valid_obs.add(lp)
        else:
            crying += 1

    frame_set = set(local_frame)
    present = valid_obs & frame_set
    missing_positions = frame_set - present
    top_missing = {p for p in missing_positions if p[1] == frame_y}
    non_top_missing = missing_positions - top_missing

    chest_world = None
    loot = None
    if tpl.get("chest"):
        cx, cy, cz = tpl["chest"]
        rx, ry, rz = rotate_pos(cx, cy, cz, size, sv.rotation, bool(sv.mirror))
        chest_world = (place_x + rx, place_y + ry, place_z + rz)
        if roll_loot:
            loot = roll_ruined_portal_chest(game_version, seed, *chest_world)

    return PortalFrameResult(
        template=key,
        giant=sv.giant,
        rotation=sv.rotation,
        mirror=bool(sv.mirror),
        valid_obsidian=len(present),
        frame_missing=len(missing_positions),
        top_missing=len(top_missing),
        non_top_missing=len(non_top_missing),
        crying_count=crying,
        chest_pos=chest_world,
        obsidian_total=len(obsidian),
        loot=loot,
    )


def bastion_type_name(variant: int) -> str:
    return {0: "housing", 1: "stables", 2: "treasure", 3: "bridge"}.get(variant, "unknown")


@dataclass
class BastionInfo:
    variant: str
    rotation: int
    start: int


def get_bastion_info(mc_version: int, seed: int, x: int, z: int) -> BastionInfo | None:
    sv = get_structure_variant(BASTION, mc_version, seed, x, z, -1)
    if sv is None:
        return None
    variant = {46: 0, 30: 1, 38: 2, 16: 3}.get(sv.sx, -1)
    return BastionInfo(variant=bastion_type_name(variant), rotation=sv.rotation, start=sv.start)


@dataclass
class VillageInfo:
    abandoned: bool
    rotation: int
    biome: int
    start: int


def get_village_info(mc_version: int, seed: int, x: int, z: int, biome_id: int) -> VillageInfo | None:
    sv = get_structure_variant(VILLAGE, mc_version, seed, x, z, biome_id)
    if sv is None:
        return None
    return VillageInfo(
        abandoned=sv.abandoned,
        rotation=sv.rotation,
        biome=sv.biome,
        start=sv.start,
    )
