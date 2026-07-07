"""EZ Seed Finder — graphical interface."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any

from ezseedfinder.paths import examples_dir

from ..engine.finder import SeedFinder, load_ezsf_file
from ..models.criteria import SearchConfig, SeedResult
from .criteria_widgets import (
    BASTION_VARIANTS,
    COMPARE_OPS,
    DIMENSIONS,
    MOB_TYPES,
    PORTAL_TEMPLATES,
    TERRAIN_TYPES,
    apply_ui_fonts,
    chest_item_row,
    dist_row,
    labeled_combo,
    labeled_entry,
    ref_row,
    resolve_ref,
    scrollable_tab,
    structure_checkbox,
    toggle_block,
)
from .ezsf_builder import build_ezsf
from .ezsf_importer import FEATURE_KEYS, apply_criteria_to_gui, parse_ezsf_to_criteria
from .structure_registry import (
    STRUCTURE_LOOT_TABLE,
    default_dist,
    structure_kind,
)


VERSIONS = [
    "1.12.2", "1.13.2", "1.14.4", "1.15.2", "1.16.1", "1.16.5",
    "1.17.1", "1.18.2", "1.19.2", "1.20", "1.21",
]

SPEEDRUN_VERSION = "1.16.1"

STRUCTURE_FIELDS = [
    ("Village", "village", "overworld"),
    ("Desert pyramid", "desert_pyramid", "overworld"),
    ("Jungle temple", "jungle_temple", "overworld"),
    ("Swamp hut", "swamp_hut", "overworld"),
    ("Igloo", "igloo", "overworld"),
    ("Ocean ruin", "ocean_ruin", "overworld"),
    ("Shipwreck", "shipwreck", "overworld"),
    ("Buried treasure", "treasure", "overworld"),
    ("Ruined portal", "ruined_portal", "overworld"),
    ("Mansion", "mansion", "overworld"),
    ("Monument", "monument", "overworld"),
    ("Pillager outpost", "outpost", "overworld"),
    ("Ancient city", "ancient_city", "overworld"),
    ("Trail ruin", "trail_ruin", "overworld"),
    ("Trial chambers", "trial_chambers", "overworld"),
    ("Nether fortress", "fortress", "nether"),
    ("Bastion", "bastion", "nether"),
    ("End city", "end_city", "end"),
]

FEATURE_LABELS = {
    "structures": "Structures",
    "spawn": "Spawn & SH",
    "biomes": "Biomes",
    "terrain": "Terrain",
    "loot": "Mobs",
}

STRUCTURE_NAMES = tuple(name for _label, name, _dim in STRUCTURE_FIELDS)


class SeedFinderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EZ Seed Finder")
        self.minsize(1280, 900)

        self._finder: SeedFinder | None = None
        self._search_thread: threading.Thread | None = None
        self._chest_rows: dict[str, list[dict[str, Any]]] = {}
        self._struct_enabled: dict[str, tk.BooleanVar] = {}
        self._struct_configs: dict[str, dict[str, Any]] = {}
        self._struct_tab_hosts: dict[str, ttk.Frame] = {}
        self._tab_hosts: dict[str, ttk.Frame] = {}
        self._feature_vars: dict[str, tk.BooleanVar] = {
            key: tk.BooleanVar(value=False) for key in FEATURE_KEYS
        }

        self._build_ui()
        self._apply_style()
        self._fit_window_to_content()

    def _apply_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        apply_ui_fonts(self)
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel", font=("Consolas", 10))

    def _fit_window_to_content(self) -> None:
        self.update_idletasks()
        width = self.winfo_reqwidth() + 24
        height = self.winfo_reqheight() + 24
        max_w = max(self.winfo_screenwidth() - 48, self.minsize()[0])
        max_h = max(self.winfo_screenheight() - 96, self.minsize()[1])
        width = min(max(width, self.minsize()[0]), max_w)
        height = min(max(height, self.minsize()[1]), max_h)
        self.geometry(f"{width}x{height}")

    def _build_ui(self) -> None:
        main = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        left = ttk.Frame(main, width=500)
        right = ttk.Frame(main)
        main.add(left, weight=1)
        main.add(right, weight=2)

        self._build_left_panel(left)
        self._build_right_panel(right)
        self._build_status_bar()

    def _build_left_panel(self, parent: ttk.Frame) -> None:
        vf = ttk.LabelFrame(parent, text="Minecraft Version", padding=8)
        vf.pack(fill=tk.X, pady=(0, 4))
        self.version_var = tk.StringVar(value=SPEEDRUN_VERSION)
        ttk.Combobox(vf, textvariable=self.version_var, values=VERSIONS, state="readonly").pack(
            fill=tk.X
        )

        self.gui_criteria_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            parent,
            text="Include GUI criteria in search",
            variable=self.gui_criteria_enabled,
        ).pack(anchor=tk.W, pady=(0, 4))

        ff = ttk.LabelFrame(parent, text="Features (show tabs)", padding=6)
        ff.pack(fill=tk.X, pady=(0, 4))
        row1 = ttk.Frame(ff)
        row1.pack(fill=tk.X)
        row2 = ttk.Frame(ff)
        row2.pack(fill=tk.X, pady=(4, 0))
        for i, key in enumerate(FEATURE_KEYS):
            parent_row = row1 if i < 4 else row2
            ttk.Checkbutton(
                parent_row,
                text=FEATURE_LABELS[key],
                variable=self._feature_vars[key],
                command=lambda k=key: self._on_feature_toggled(k),
            ).pack(side=tk.LEFT, padx=(0, 10))

        self._notebook = ttk.Notebook(parent)
        self._notebook.pack(fill=tk.BOTH, expand=True, pady=4)

        self._build_structures_tab()
        self._build_structure_config_tabs()
        self._build_spawn_tab()
        self._build_biomes_tab()
        self._build_terrain_tab()
        self._build_mobs_tab()
        self._search_outer = ttk.Frame(self._notebook)
        self._build_search_tab(self._search_outer)
        self._notebook.add(self._search_outer, text="Search")
        self._refresh_tabs()

        bf = ttk.Frame(parent)
        bf.pack(fill=tk.X, pady=6)
        ttk.Button(bf, text="Export GUI → .ezsf", command=self._export_gui_to_ezsf).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(bf, text="Preview GUI .ezsf", command=self._preview_gui_ezsf).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        self.start_btn = ttk.Button(bf, text="▶  Start", command=self._start_search)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.stop_btn = ttk.Button(bf, text="■  Stop", command=self._stop_search, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)

    def _make_tab_host(self, key: str) -> ttk.Frame:
        outer = ttk.Frame(self._notebook)
        self._tab_hosts[key] = outer
        return scrollable_tab(outer)

    def _current_tab_key(self) -> str | None:
        try:
            selected = self._notebook.select()
        except tk.TclError:
            return None
        if str(selected) == str(self._search_outer):
            return "search"
        for name, frame in self._struct_tab_hosts.items():
            if str(frame) == str(selected):
                return name
        for key, frame in self._tab_hosts.items():
            if str(frame) == str(selected):
                return key
        return None

    def _tab_visible(self, key: str) -> bool:
        if key == "search":
            return True
        frame = self._struct_tab_hosts.get(key) or self._tab_hosts.get(key)
        if frame is None:
            return False
        return str(frame) in [str(t) for t in self._notebook.tabs()]

    def _refresh_tabs(self, select: str | None = None) -> None:
        stay_on = None if select else self._current_tab_key()

        for tab_id in list(self._notebook.tabs()):
            if str(tab_id) != str(self._search_outer):
                self._notebook.forget(tab_id)

        insert_at = self._notebook.index(self._search_outer)

        if self._feature_vars["structures"].get() and "structures" in self._tab_hosts:
            self._notebook.insert(insert_at, self._tab_hosts["structures"], text="Structures")
            insert_at += 1
            for label, name, _dim in STRUCTURE_FIELDS:
                if self._struct_enabled[name].get() and name in self._struct_tab_hosts:
                    self._notebook.insert(
                        insert_at,
                        self._struct_tab_hosts[name],
                        text=label,
                    )
                    insert_at += 1

        for key in FEATURE_KEYS:
            if key == "structures":
                continue
            if self._feature_vars[key].get() and key in self._tab_hosts:
                self._notebook.insert(
                    self._notebook.index(self._search_outer),
                    self._tab_hosts[key],
                    text=FEATURE_LABELS[key],
                )

        if select:
            self._select_tab(select)
        elif stay_on and self._tab_visible(stay_on):
            self._select_tab(stay_on)
        elif stay_on and self._tab_visible("structures"):
            self._select_tab("structures")

    def _select_tab(self, key: str) -> None:
        if key == "search":
            try:
                self._notebook.select(self._search_outer)
            except tk.TclError:
                pass
            return
        frame = self._struct_tab_hosts.get(key) or self._tab_hosts.get(key)
        if frame is None:
            return
        try:
            self._notebook.select(frame)
        except tk.TclError:
            pass

    def _on_feature_toggled(self, key: str) -> None:
        select = key if self._feature_vars[key].get() else None
        self._refresh_tabs(select=select)

    def _on_structure_toggled(self, name: str) -> None:
        if any(v.get() for v in self._struct_enabled.values()):
            self._feature_vars["structures"].set(True)
        select = name if self._struct_enabled[name].get() else None
        self._refresh_tabs(select=select)

    def _build_structures_tab(self) -> None:
        tab = self._make_tab_host("structures")
        ttk.Label(tab, text="Select structures — each opens its own config tab", style="Header.TLabel").pack(
            anchor=tk.W, pady=(0, 6)
        )
        picker = ttk.Frame(tab)
        picker.pack(fill=tk.X)

        col_a = ttk.Frame(picker)
        col_b = ttk.Frame(picker)
        col_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        col_b.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        mid = (len(STRUCTURE_FIELDS) + 1) // 2
        for i, (label, name, _dim) in enumerate(STRUCTURE_FIELDS):
            parent_col = col_a if i < mid else col_b
            enabled = structure_checkbox(parent_col, label)
            enabled.trace_add("write", lambda *_a, n=name: self._on_structure_toggled(n))
            self._struct_enabled[name] = enabled

        body, self.struct_between_enabled = toggle_block(tab, "Two structures near same point")
        self.struct_between_a = labeled_combo(body, "Structure A", STRUCTURE_NAMES, "village")
        self.struct_between_b = labeled_combo(body, "Structure B", STRUCTURE_NAMES, "treasure")
        self.struct_between_dim = labeled_combo(body, "Dimension", DIMENSIONS, "overworld")
        self.struct_between_ref = ref_row(body, "spawn")
        self.struct_between_dist = dist_row(body, "800")

        body, self.dist_rule_enabled = toggle_block(tab, "Distance between structures")
        self.dist_rule_a = labeled_combo(body, "From", STRUCTURE_NAMES, "village")
        self.dist_rule_b = labeled_combo(body, "To", STRUCTURE_NAMES, "treasure")
        self.dist_rule_op = labeled_combo(body, "Operator", COMPARE_OPS, "<=")
        self.dist_rule_value = labeled_entry(body, "Distance (blocks)", "200")
        self.dist_rule_dim = labeled_combo(body, "Dimension", DIMENSIONS, "overworld")

    def _make_struct_tab_host(self, name: str) -> ttk.Frame:
        outer = ttk.Frame(self._notebook)
        self._struct_tab_hosts[name] = outer
        return scrollable_tab(outer)

    def _build_structure_config_tabs(self) -> None:
        for label, name, dim in STRUCTURE_FIELDS:
            tab = self._make_struct_tab_host(name)
            kind = structure_kind(name)
            cfg: dict[str, Any] = {"kind": kind, "dimension": dim, "label": label}

            if kind == "portal":
                cfg["dimension_var"] = labeled_combo(tab, "Dimension", ("overworld", "nether"), dim)
                cfg["ref"] = ref_row(tab, "spawn")
                cfg["max_dist"] = dist_row(tab, default_dist(name))
                cfg["viable"] = tk.BooleanVar(value=True)
                ttk.Checkbutton(tab, text="Must be viable", variable=cfg["viable"]).pack(anchor=tk.W)
                ttk.Label(tab, text="Variant", style="Header.TLabel").pack(anchor=tk.W, pady=(8, 2))
                cfg["giant"] = labeled_combo(tab, "Giant portal", ("", "false", "true"), "false")
                cfg["template"] = labeled_combo(tab, "Template (1–10)", PORTAL_TEMPLATES, "6")
                cfg["underground"] = labeled_combo(tab, "Underground", ("", "false", "true"), "")
                cfg["airpocket"] = labeled_combo(tab, "Air pocket", ("", "false", "true"), "")
                ttk.Label(tab, text="Frame (after crying obsidian)", style="Header.TLabel").pack(
                    anchor=tk.W, pady=(8, 2)
                )
                cfg["top_missing"] = labeled_entry(tab, "Top row missing", "1")
                cfg["frame_missing"] = labeled_entry(tab, "Total frame missing", "1")
                ttk.Label(
                    tab,
                    text="portal_6 = 5×5 frame, 1 missing at top center",
                    font=("Segoe UI", 8),
                ).pack(anchor=tk.W)
                ttk.Label(tab, text="Chest loot requirements", style="Header.TLabel").pack(
                    anchor=tk.W, pady=(8, 2)
                )
                cfg["chest_frame"] = ttk.Frame(tab)
                cfg["chest_frame"].pack(fill=tk.X)
                self._struct_configs[name] = cfg
                self._chest_rows[name] = []
                ttk.Button(
                    tab,
                    text="+ Add chest item",
                    command=lambda n=name: self._add_chest_row(n),
                ).pack(anchor=tk.W, pady=4)
                self._add_chest_row(name, "obsidian", "1")
                self._add_chest_row(name, "flint_and_steel", "1")
                continue

            elif kind == "bastion":
                cfg["variant"] = labeled_combo(tab, "Variant", BASTION_VARIANTS, "treasure")
                cfg["ref"] = ref_row(tab, "0,0")
                cfg["max_dist"] = dist_row(tab, default_dist(name))
                cfg["viable"] = tk.BooleanVar(value=True)
                ttk.Checkbutton(tab, text="Must be viable", variable=cfg["viable"]).pack(anchor=tk.W)

            elif kind == "loot_chest":
                table = STRUCTURE_LOOT_TABLE[name]
                cfg["loot_table"] = table
                self._struct_configs[name] = cfg
                ttk.Label(tab, text=f"Loot table: {table}", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 6))
                cfg["ref"] = ref_row(tab, "spawn")
                cfg["max_dist"] = dist_row(tab, default_dist(name))
                cfg["viable"] = tk.BooleanVar(value=True)
                ttk.Checkbutton(tab, text="Must be viable", variable=cfg["viable"]).pack(anchor=tk.W)
                ttk.Label(tab, text="Chest loot requirements", style="Header.TLabel").pack(
                    anchor=tk.W, pady=(8, 2)
                )
                cfg["chest_frame"] = ttk.Frame(tab)
                cfg["chest_frame"].pack(fill=tk.X)
                ttk.Button(
                    tab,
                    text="+ Add chest item",
                    command=lambda n=name: self._add_chest_row(n),
                ).pack(anchor=tk.W, pady=4)
                self._chest_rows[name] = []
                default_item = "heart_of_the_sea" if name == "treasure" else "gold_ingot"
                self._add_chest_row(name, default_item, "1")
                continue

            else:
                cfg["ref"] = ref_row(tab, "spawn")
                cfg["max_dist"] = dist_row(tab, default_dist(name))
                cfg["viable"] = tk.BooleanVar(value=True)
                ttk.Checkbutton(tab, text="Must be viable", variable=cfg["viable"]).pack(anchor=tk.W)

            self._struct_configs[name] = cfg

    def _add_chest_row(self, struct_name: str, item: str = "obsidian", count: str = "1") -> None:
        cfg = self._struct_configs[struct_name]
        frame = cfg["chest_frame"]
        row = chest_item_row(frame)

        def remove() -> None:
            row["row"].destroy()
            self._chest_rows[struct_name].remove(row)

        ttk.Button(row["row"], text="−", width=3, command=remove).pack(side=tk.RIGHT)
        row["item"].set(item)
        row["count"].set(count)
        self._chest_rows[struct_name].append(row)

    def _collect_chest_items(self, struct_name: str) -> list[tuple[str, int]]:
        items: list[tuple[str, int]] = []
        for row in self._chest_rows.get(struct_name, []):
            item = row["item"].get().strip()
            if item:
                items.append((item, row["count"].get()))
        return items

    def _build_spawn_tab(self) -> None:
        tab = self._make_tab_host("spawn")

        body, self.spawn_require_dist = toggle_block(tab, "Spawn within distance")
        self.spawn_ref = ref_row(body, "origin")
        self.spawn_max_dist = dist_row(body, "0")
        self.spawn_biomes = labeled_entry(body, "Spawn biome(s)", "", 20)
        ttk.Label(body, text="Use | for multiple, e.g. plains | forest").pack(anchor=tk.W)

        body, self.stronghold_require = toggle_block(tab, "Stronghold requirements")
        self.sh_nearest_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="Nearest stronghold within", variable=self.sh_nearest_enabled).pack(
            anchor=tk.W
        )
        self.sh_nearest_dist = dist_row(body, "1500")
        self.sh_nearest_ref = ref_row(body, "spawn")
        self.sh_under_spawn = tk.BooleanVar(value=False)
        self.sh_full = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="Under spawn (~250 blocks)", variable=self.sh_under_spawn).pack(
            anchor=tk.W
        )
        ttk.Checkbutton(body, text="Full stronghold (ring-1 heuristic)", variable=self.sh_full).pack(
            anchor=tk.W
        )
        self.sh_ring_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="Specific ring", variable=self.sh_ring_enabled).pack(anchor=tk.W)
        self.sh_ring = labeled_entry(body, "Ring number", "1")

    def _build_biomes_tab(self) -> None:
        tab = self._make_tab_host("biomes")

        body, self.biome_at_require = toggle_block(tab, "Biome at coordinates")
        self.biome_at_dim = labeled_combo(body, "Dimension", DIMENSIONS, "overworld")
        self.biome_at_x = labeled_entry(body, "X", "0")
        self.biome_at_y = labeled_entry(body, "Y", "64")
        self.biome_at_z = labeled_entry(body, "Z", "0")
        self.biome_at_names = labeled_entry(body, "Biome(s)", "plains | forest", 20)
        self.biome_at_negate = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="Exclude these biomes (not)", variable=self.biome_at_negate).pack(
            anchor=tk.W
        )

        body, self.biome_region_require = toggle_block(tab, "Biome region percent")
        self.biome_region_dim = labeled_combo(body, "Dimension", DIMENSIONS, "overworld")
        self.biome_region_x1 = labeled_entry(body, "X1", "-512")
        self.biome_region_z1 = labeled_entry(body, "Z1", "-512")
        self.biome_region_x2 = labeled_entry(body, "X2", "512")
        self.biome_region_z2 = labeled_entry(body, "Z2", "512")
        self.biome_region_y = labeled_entry(body, "Y", "64")
        self.biome_region_op = labeled_combo(body, "Operator", (">=", "<=", "==", "contains"), ">=")
        self.biome_region_biome = labeled_entry(body, "Biome", "desert")
        self.biome_region_pct = labeled_entry(body, "Percent", "10")

    def _build_terrain_tab(self) -> None:
        tab = self._make_tab_host("terrain")

        body, self.terrain_require = toggle_block(tab, "Terrain predicate")
        self.terrain_dim = labeled_combo(body, "Dimension", DIMENSIONS, "overworld")
        self.terrain_x = labeled_entry(body, "X", "0")
        self.terrain_z = labeled_entry(body, "Z", "0")
        self.terrain_radius = labeled_entry(body, "Radius", "128")
        self.terrain_pred = labeled_combo(body, "Type", TERRAIN_TYPES, "flat")
        self.terrain_negate = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="Invert (not)", variable=self.terrain_negate).pack(anchor=tk.W)

        body, self.height_require = toggle_block(tab, "Height at coordinates")
        self.height_dim = labeled_combo(body, "Dimension", DIMENSIONS, "overworld")
        self.height_x = labeled_entry(body, "X", "0")
        self.height_z = labeled_entry(body, "Z", "0")
        self.height_op = labeled_combo(body, "Operator", COMPARE_OPS, ">=")
        self.height_value = labeled_entry(body, "Y value", "64")

    def _build_mobs_tab(self) -> None:
        tab = self._make_tab_host("loot")

        self.mob_type = labeled_combo(tab, "Mob", MOB_TYPES, "witch")
        self.mob_dim = labeled_combo(tab, "Dimension", DIMENSIONS, "overworld")
        self.mob_ref = ref_row(tab, "spawn")
        self.mob_dist = dist_row(tab, "200")
        self.mob_biomes = labeled_entry(tab, "Biome(s)", "swamp", 20)
        ttk.Label(tab, text="Use | for multiple biomes, e.g. swamp | mangrove_swamp").pack(anchor=tk.W)

    def _build_search_tab(self, tab: ttk.Frame) -> None:

        sf = ttk.LabelFrame(tab, text="Search settings", padding=8)
        sf.pack(fill=tk.X, pady=4)
        self.max_results_var = labeled_entry(sf, "Max results", "10")
        self.threads_var = labeled_entry(sf, "Threads (0=auto)", "0")
        self.random_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(sf, text="Random search", variable=self.random_var).pack(anchor=tk.W)
        self.seed_start_var = labeled_entry(sf, "Seed start (optional)", "")
        self.seed_end_var = labeled_entry(sf, "Seed end (optional)", "")

        # Legacy quick filters still used by _check_gui for simple distance-only searches
        lf = ttk.LabelFrame(tab, text="Quick distance filters (legacy)", padding=8)
        lf.pack(fill=tk.X, pady=4)
        ttk.Label(lf, text="Also checked directly (no .ezsf needed)").pack(anchor=tk.W, pady=(0, 4))
        inner = ttk.Frame(lf)
        inner.pack(fill=tk.X)
        self.dist_vars: dict[str, tk.StringVar] = {}
        self.dist_enabled: dict[str, tk.BooleanVar] = {}
        self.dist_entries: dict[str, ttk.Entry] = {}
        legacy = [
            ("Village", "village_dist"),
            ("Ruined portal", "ruined_portal_dist"),
            ("Stronghold", "stronghold_dist"),
            ("Bastion", "bastion_dist"),
            ("Fortress", "fortress_dist"),
        ]
        for label, key in legacy:
            row = ttk.Frame(inner)
            row.pack(fill=tk.X, pady=2)
            enabled = tk.BooleanVar(value=False)
            self.dist_enabled[key] = enabled
            ttk.Checkbutton(row, variable=enabled, width=2).pack(side=tk.LEFT, padx=(0, 4))
            ttk.Label(row, text=label, width=16).pack(side=tk.LEFT)
            var = tk.StringVar(value="500" if key == "village_dist" else "0")
            self.dist_vars[key] = var
            entry = ttk.Entry(row, textvariable=var, width=10)
            entry.pack(side=tk.RIGHT)
            self.dist_entries[key] = entry
            enabled.trace_add("write", lambda *_a, k=key: self._toggle_dist_field(k))
            self._toggle_dist_field(key)

        self.stronghold_under = tk.BooleanVar(value=False)
        self.stronghold_full = tk.BooleanVar(value=False)
        self.spawn_dist_enabled = tk.BooleanVar(value=False)
        self.spawn_dist_var = tk.StringVar(value="0")
        self.spawn_biome_enabled = tk.BooleanVar(value=False)
        self.spawn_biome_var = tk.StringVar(value="")

    def _build_right_panel(self, parent: ttk.Frame) -> None:
        ef = ttk.LabelFrame(parent, text=".ezsf Criteria (text)", padding=6)
        ef.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        toolbar = ttk.Frame(ef)
        toolbar.pack(fill=tk.X, pady=(0, 4))
        self.ezsf_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(toolbar, text="Also use .ezsf text below", variable=self.ezsf_enabled).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(toolbar, text="Load .ezsf", command=self._load_ezsf).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(toolbar, text="Import → GUI", command=self._import_ezsf_to_gui).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(toolbar, text="Save .ezsf", command=self._save_ezsf).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(toolbar, text="Load Example", command=self._load_example).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(toolbar, text="Speedrun 1.16.1", command=self._load_speedrun_example).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(toolbar, text="Ruined Portal", command=self._load_ruined_portal_example).pack(side=tk.LEFT)
        self.ezsf_enabled.trace_add("write", lambda *_: self._toggle_ezsf_editor())

        self.ezsf_text = scrolledtext.ScrolledText(
            ef, wrap=tk.NONE, font=("Consolas", 10), height=14, undo=True
        )
        self.ezsf_text.pack(fill=tk.BOTH, expand=True)
        self._load_example(initial=True)
        self._toggle_ezsf_editor()

        rf = ttk.LabelFrame(parent, text="Results", padding=6)
        rf.pack(fill=tk.BOTH, expand=True)

        cols = ("seed", "spawn", "details")
        self.results_tree = ttk.Treeview(rf, columns=cols, show="headings", height=8)
        self.results_tree.heading("seed", text="Seed")
        self.results_tree.heading("spawn", text="Spawn")
        self.results_tree.heading("details", text="Details")
        self.results_tree.column("seed", width=200)
        self.results_tree.column("spawn", width=130)
        self.results_tree.column("details", width=520)
        rsb = ttk.Scrollbar(rf, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=rsb.set)
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.results_tree.bind("<Double-1>", self._copy_seed)
        ttk.Label(rf, text="Double-click a seed to copy").pack(anchor=tk.W)

    def _build_status_bar(self) -> None:
        bar = ttk.Frame(self, padding=(8, 4))
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(bar, textvariable=self.status_var, style="Status.TLabel").pack(side=tk.LEFT)
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=200)
        self.progress.pack(side=tk.RIGHT)

    def _toggle_dist_field(self, key: str) -> None:
        entry = self.dist_entries.get(key)
        if entry is None:
            return
        entry.configure(state="normal" if self.dist_enabled[key].get() else "disabled")

    def _toggle_ezsf_editor(self) -> None:
        state = "normal" if self.ezsf_enabled.get() else "disabled"
        self.ezsf_text.configure(state=state)

    def _collect_gui_criteria(self) -> dict[str, Any]:
        structures: list[dict[str, Any]] = []
        loot_rules: list[dict[str, Any]] = []
        ruined_portal: dict[str, Any] = {"enabled": False}
        bastion: dict[str, Any] = {"enabled": False}

        for label, name, dim in STRUCTURE_FIELDS:
            if not self._struct_enabled[name].get():
                continue
            cfg = self._struct_configs[name]
            ref, ref_pos = resolve_ref(cfg["ref"])
            kind = cfg["kind"]

            if kind == "portal":
                giant = cfg["giant"].get().strip()
                underground = cfg["underground"].get().strip()
                airpocket = cfg["airpocket"].get().strip()
                template = cfg["template"].get().strip()
                ruined_portal = {
                    "enabled": True,
                    "dimension": cfg["dimension_var"].get(),
                    "ref": ref,
                    "ref_pos": ref_pos,
                    "max_dist": cfg["max_dist"].get(),
                    "viable": cfg["viable"].get(),
                    "giant": giant or None,
                    "template": template or None,
                    "underground": underground or None,
                    "airpocket": airpocket or None,
                    "top_missing": cfg["top_missing"].get(),
                    "frame_missing": cfg["frame_missing"].get(),
                    "chest_items": self._collect_chest_items(name),
                }
            elif kind == "bastion":
                bastion = {
                    "enabled": True,
                    "variant": cfg["variant"].get(),
                    "ref": ref,
                    "ref_pos": ref_pos,
                    "max_dist": cfg["max_dist"].get(),
                    "viable": cfg["viable"].get(),
                }
            elif kind == "loot_chest":
                structures.append(
                    {
                        "enabled": True,
                        "name": name,
                        "dimension": dim,
                        "ref": ref,
                        "ref_pos": ref_pos,
                        "max_dist": cfg["max_dist"].get(),
                        "viable": cfg["viable"].get(),
                    }
                )
                for item, count in self._collect_chest_items(name):
                    loot_rules.append(
                        {
                            "enabled": True,
                            "structure": name,
                            "loot_table": cfg["loot_table"],
                            "item": item,
                            "min_count": str(count),
                            "dimension": dim,
                            "ref": ref,
                            "ref_pos": ref_pos,
                            "max_dist": cfg["max_dist"].get(),
                        }
                    )
            else:
                structures.append(
                    {
                        "enabled": True,
                        "name": name,
                        "dimension": dim,
                        "ref": ref,
                        "ref_pos": ref_pos,
                        "max_dist": cfg["max_dist"].get(),
                        "viable": cfg["viable"].get(),
                    }
                )

        s_ref, s_ref_pos = resolve_ref(self.spawn_ref)
        sh_ref, sh_ref_pos = resolve_ref(self.sh_nearest_ref)

        return {
            "emit_version": False,
            "threads": self.threads_var.get(),
            "max_results": self.max_results_var.get(),
            "seed_start": self.seed_start_var.get().strip() or None,
            "seed_end": self.seed_end_var.get().strip() or None,
            "random_search": self.random_var.get(),
            "spawn": {
                "enabled": self.spawn_require_dist.get(),
                "ref": s_ref,
                "ref_pos": s_ref_pos,
                "max_dist": self.spawn_max_dist.get(),
                "biomes": self.spawn_biomes.get(),
            },
            "stronghold": {
                "enabled": self.stronghold_require.get(),
                "nearest_enabled": self.sh_nearest_enabled.get(),
                "nearest_dist": self.sh_nearest_dist.get(),
                "nearest_ref": sh_ref,
                "nearest_ref_pos": sh_ref_pos,
                "under_spawn": self.sh_under_spawn.get(),
                "full": self.sh_full.get(),
                "ring": self.sh_ring.get() if self.sh_ring_enabled.get() else None,
            },
            "structures": structures,
            "ruined_portal": ruined_portal,
            "bastion": bastion,
            "biomes": [
                {
                    "enabled": self.biome_at_require.get(),
                    "dimension": self.biome_at_dim.get(),
                    "x": self.biome_at_x.get(),
                    "y": self.biome_at_y.get(),
                    "z": self.biome_at_z.get(),
                    "names": self.biome_at_names.get(),
                    "negate": self.biome_at_negate.get(),
                }
            ],
            "biome_regions": [
                {
                    "enabled": self.biome_region_require.get(),
                    "dimension": self.biome_region_dim.get(),
                    "x1": self.biome_region_x1.get(),
                    "z1": self.biome_region_z1.get(),
                    "x2": self.biome_region_x2.get(),
                    "z2": self.biome_region_z2.get(),
                    "y": self.biome_region_y.get(),
                    "op": self.biome_region_op.get(),
                    "biome": self.biome_region_biome.get(),
                    "percent": self.biome_region_pct.get(),
                }
            ],
            "terrain": [
                {
                    "enabled": self.terrain_require.get(),
                    "dimension": self.terrain_dim.get(),
                    "x": self.terrain_x.get(),
                    "z": self.terrain_z.get(),
                    "radius": self.terrain_radius.get(),
                    "predicate": self.terrain_pred.get(),
                    "negate": self.terrain_negate.get(),
                }
            ],
            "heights": [
                {
                    "enabled": self.height_require.get(),
                    "dimension": self.height_dim.get(),
                    "x": self.height_x.get(),
                    "z": self.height_z.get(),
                    "op": self.height_op.get(),
                    "value": self.height_value.get(),
                }
            ],
            "loot": loot_rules,
            "mobs": [
                {
                    "enabled": self._feature_vars["loot"].get(),
                    "mob": self.mob_type.get(),
                    "dimension": self.mob_dim.get(),
                    **dict(zip(("ref", "ref_pos"), resolve_ref(self.mob_ref), strict=True)),
                    "max_dist": self.mob_dist.get(),
                    "biomes": self.mob_biomes.get(),
                }
            ],
            "structure_between": [
                {
                    "enabled": self.struct_between_enabled.get(),
                    "dimension": self.struct_between_dim.get(),
                    "structure_a": self.struct_between_a.get(),
                    "structure_b": self.struct_between_b.get(),
                    **dict(zip(("ref", "ref_pos"), resolve_ref(self.struct_between_ref), strict=True)),
                    "max_dist": self.struct_between_dist.get(),
                    "viable": True,
                }
            ],
            "distance_rules": [
                {
                    "enabled": self.dist_rule_enabled.get(),
                    "dimension": self.dist_rule_dim.get(),
                    "a": self.dist_rule_a.get(),
                    "b": self.dist_rule_b.get(),
                    "op": self.dist_rule_op.get(),
                    "value": self.dist_rule_value.get(),
                }
            ],
        }

    def _merged_ezsf_text(self) -> str:
        parts: list[str] = []
        if self.gui_criteria_enabled.get():
            gui_ezsf = build_ezsf(self._collect_gui_criteria(), version=self.version_var.get())
            if gui_ezsf:
                parts.append(gui_ezsf)
        if self.ezsf_enabled.get():
            user = self.ezsf_text.get("1.0", tk.END).strip()
            if user:
                parts.append(user)
        return "\n\n".join(parts)

    def _export_gui_to_ezsf(self) -> None:
        text = build_ezsf(self._collect_gui_criteria(), version=self.version_var.get())
        if not text:
            messagebox.showinfo("Export", "No enabled GUI criteria to export.")
            return
        self.ezsf_enabled.set(True)
        self._set_ezsf_content(text)
        self.status_var.set("Exported GUI criteria to .ezsf editor")

    def _import_ezsf_to_gui(self) -> None:
        text = self.ezsf_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Import", "No .ezsf text to import.")
            return
        try:
            criteria, features, doc = parse_ezsf_to_criteria(text)
            if doc.version:
                self.version_var.set(doc.version)
            apply_criteria_to_gui(self, criteria, features)
            self.gui_criteria_enabled.set(True)
            self.status_var.set("Imported .ezsf into GUI fields")
        except Exception as exc:
            messagebox.showerror("Import Error", str(exc))

    def _preview_gui_ezsf(self) -> None:
        text = build_ezsf(self._collect_gui_criteria(), version=self.version_var.get())
        if not text:
            messagebox.showinfo("Preview", "No enabled GUI criteria.")
            return
        self.ezsf_enabled.set(True)
        self._set_ezsf_content(text)
        self.status_var.set("Loaded GUI criteria preview into .ezsf editor")

    def _load_ruined_portal_example(self) -> None:
        path = examples_dir() / "ruined_portal_speedrun.ezsf"
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                content = f.read()
            self._set_ezsf_content(content)
            self.ezsf_enabled.set(True)
            try:
                criteria, features, doc = parse_ezsf_to_criteria(content)
                if doc.version:
                    self.version_var.set(doc.version)
                apply_criteria_to_gui(self, criteria, features)
            except Exception:
                pass
        self.gui_criteria_enabled.set(True)
        self.status_var.set("Loaded ruined portal speedrun preset")

    def _load_speedrun_example(self) -> None:
        path = examples_dir() / "speedrun.ezsf"
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                self._set_ezsf_content(f.read())
        else:
            self._set_ezsf_content(self._speedrun_ezsf_text())
        self.version_var.set(SPEEDRUN_VERSION)
        self.ezsf_enabled.set(True)
        self.status_var.set("Loaded 1.16.1 speedrun preset")

    def _speedrun_ezsf_text(self) -> str:
        return """# 1.16.1 speedrun seed — village, portal, stronghold, nether
version 1.16.1
max_results 5
threads 8

spawn within 1500 of origin

dimension overworld {
  structure village within 400 of spawn viable
  ruined_portal within 250 of spawn viable
}

stronghold nearest within 1200 of spawn

distance village ruined_portal <= 200 in overworld

dimension nether {
  bastion variant treasure within 800 of 0,0 viable
  structure fortress within 600 of 0,0 viable
}
"""

    def _load_example(self, initial: bool = False) -> None:
        example = """# Optional extra .ezsf rules (merged with GUI tabs when enabled)
# version 1.16.1
# threads 8
# max_results 5
"""
        if initial or messagebox.askyesno("Load Example", "Replace current .ezsf text with example?"):
            self._set_ezsf_content(example)

    def _set_ezsf_content(self, text: str) -> None:
        self.ezsf_text.configure(state="normal")
        self.ezsf_text.delete("1.0", tk.END)
        self.ezsf_text.insert("1.0", text)
        self._toggle_ezsf_editor()

    def _load_ezsf(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("EZ Seed Finder", "*.ezsf"), ("All files", "*.*")]
        )
        if path:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            self._set_ezsf_content(content)
            self.ezsf_enabled.set(True)
            try:
                criteria, features, doc = parse_ezsf_to_criteria(content)
                if doc.version:
                    self.version_var.set(doc.version)
                apply_criteria_to_gui(self, criteria, features)
                self.gui_criteria_enabled.set(True)
            except Exception as exc:
                messagebox.showwarning("Import", f"Loaded file but GUI import failed: {exc}")
            self.status_var.set(f"Loaded {os.path.basename(path)}")

    def _save_ezsf(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".ezsf",
            filetypes=[("EZ Seed Finder", "*.ezsf")],
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._merged_ezsf_text())
            self.status_var.set(f"Saved {os.path.basename(path)}")

    def _build_config(self) -> SearchConfig:
        merged_ezsf = self._merged_ezsf_text()
        gui_filters: dict = {
            "version": self.version_var.get(),
            "stronghold_under_spawn": self.stronghold_under.get() or self.sh_under_spawn.get(),
            "stronghold_full": self.stronghold_full.get() or self.sh_full.get(),
            "ezsf_enabled": bool(merged_ezsf.strip()),
            "ezsf_text": merged_ezsf,
        }
        for key, var in self.dist_vars.items():
            gui_filters[f"{key}_enabled"] = self.dist_enabled[key].get()
            if self.dist_enabled[key].get():
                try:
                    gui_filters[key] = int(var.get() or "0")
                except ValueError:
                    gui_filters[key] = 0

        if self.spawn_require_dist.get():
            gui_filters["spawn_dist_enabled"] = True
            try:
                gui_filters["spawn_max_dist"] = int(self.spawn_max_dist.get() or "0")
            except ValueError:
                gui_filters["spawn_max_dist"] = 0
            biomes = self.spawn_biomes.get().strip()
            if biomes:
                gui_filters["spawn_biome_enabled"] = True
                gui_filters["spawn_biome"] = biomes

        try:
            max_results = int(self.max_results_var.get() or "10")
        except ValueError:
            max_results = 10

        try:
            threads = int(self.threads_var.get() or "0")
        except ValueError:
            threads = 0

        seed_start = self.seed_start_var.get().strip()
        seed_end = self.seed_end_var.get().strip()

        return SearchConfig(
            version=self.version_var.get(),
            threads=threads,
            max_results=max_results,
            seed_start=int(seed_start) if seed_start else None,
            seed_end=int(seed_end) if seed_end else None,
            random_search=self.random_var.get(),
            gui_filters=gui_filters,
        )

    def _start_search(self) -> None:
        if self._search_thread and self._search_thread.is_alive():
            return

        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        config = self._build_config()
        self._finder = SeedFinder(config)

        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.progress.start(12)
        self.status_var.set("Searching...")

        def run():
            try:
                self._finder.search(
                    on_result=lambda r: self.after(0, lambda: self._add_result(r)),
                    on_progress=lambda n, rate: self.after(
                        0, lambda: self.status_var.set(f"Searched {n:,} seeds @ {rate:,.0f}/s")
                    ),
                )
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Search Error", str(exc)))
            finally:
                self.after(0, self._search_finished)

        self._search_thread = threading.Thread(target=run, daemon=True)
        self._search_thread.start()

    def _stop_search(self) -> None:
        if self._finder:
            self._finder.stop()

    def _search_finished(self) -> None:
        self.progress.stop()
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        count = len(self._finder.results) if self._finder else 0
        rate = self._finder.rate if self._finder else 0
        self.status_var.set(f"Done — found {count} seed(s) @ {rate:,.0f} seeds/s")

    def _add_result(self, result: SeedResult) -> None:
        spawn = result.details.get("spawn", ("?", "?"))
        spawn_str = f"{spawn[0]}, {spawn[1]}"
        detail_parts = []
        for k, v in result.details.items():
            if k == "spawn":
                continue
            detail_parts.append(f"{k}={v}")
        details = "; ".join(detail_parts[:6])
        self.results_tree.insert("", tk.END, values=(result.seed, spawn_str, details))

    def _copy_seed(self, _event=None) -> None:
        sel = self.results_tree.selection()
        if sel:
            seed = self.results_tree.item(sel[0])["values"][0]
            self.clipboard_clear()
            self.clipboard_append(str(seed))
            self.status_var.set(f"Copied seed {seed}")


def run_app() -> None:
    app = SeedFinderApp()
    app.mainloop()
