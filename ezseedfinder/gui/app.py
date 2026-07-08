"""EZ Seed Finder — graphical interface."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

import customtkinter as ctk

from ezseedfinder import __version__
from ezseedfinder.paths import examples_dir

from ..engine.finder import SeedFinder, load_ezsf_file
from ..engine.checker import SeedChecker
from ..engine.loot_tables import loot_data_version, loot_table_item_names
from ..models.criteria import SearchConfig, SeedResult
from .criteria_widgets import (
    BASTION_VARIANTS,
    COMPARE_OPS,
    DEFAULT_LOOT_ITEMS,
    DIMENSIONS,
    MOB_TYPES,
    PORTAL_TEMPLATES,
    TERRAIN_TYPES,
    chest_item_row,
    dist_row,
    labeled_combo,
    labeled_entry,
    muted,
    ref_row,
    resolve_ref,
    scrollable_tab,
    structure_checkbox,
    toggle_block,
)
from .theme import (
    COLORS,
    TAB_BODY_INSET,
    TAB_BODY_RADIUS,
    btn_danger,
    btn_primary,
    btn_secondary,
    card,
    card_title,
    checkbox,
    combo,
    embed_treeview,
    heading,
    mini_btn,
    muted,
    setup_theme,
    tab_button,
    textbox,
)
from .export_results import write_results
from .ezsf_builder import build_ezsf
from .ezsf_importer import FEATURE_KEYS, apply_criteria_to_gui, parse_ezsf_to_criteria
from .splash import StartupOverlay, TabLoadOverlay
from .widgets import IndeterminateProgressBar
from .structure_registry import (
    STRUCTURE_LOOT_TABLE,
    default_dist,
    structure_kind,
)


VERSIONS = [
    "1.12.2", "1.13.2", "1.14.4", "1.15.2", "1.16.1", "1.16.5",
    "1.17.1", "1.18.2", "1.19.2", "1.20", "1.21",
    "26.1.2", "26.2",
]

DEFAULT_VERSION = "26.2"
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

PRESETS: tuple[tuple[str, str], ...] = (
    ("1.16.1 Portal speedrun", "ruined_portal_speedrun.ezsf"),
    ("1.16.1 Full speedrun", "speedrun.ezsf"),
    ("Advanced multi-dim", "advanced.ezsf"),
    ("Mushroom island", "mushroom_island.ezsf"),
)


class SeedFinderApp(ctk.CTk):
    def __init__(self):
        setup_theme()
        super().__init__(fg_color=COLORS["bg"])
        self.title(f"EZ Seed Finder v{__version__}")
        self.minsize(1280, 900)
        self.geometry("1360x920")

        self._finder: SeedFinder | None = None
        self._search_thread: threading.Thread | None = None
        self._syncing = False
        self._gui_to_ezsf_after: str | None = None
        self._ezsf_to_gui_after: str | None = None
        self._chest_rows: dict[str, list[dict[str, Any]]] = {}
        self._results: list[SeedResult] = []
        self._paused = False
        self._struct_enabled: dict[str, tk.BooleanVar] = {}
        self._struct_configs: dict[str, dict[str, Any]] = {}
        self._struct_built: set[str] = set()
        self._feature_built: set[str] = set()
        self._struct_tab_hosts: dict[str, ctk.CTkFrame] = {}
        self._tab_hosts: dict[str, ctk.CTkFrame] = {}
        self._tab_frames: dict[str, ctk.CTkFrame] = {}
        self._tab_buttons: dict[str, ctk.CTkButton] = {}
        self._tab_labels: dict[str, str] = {"search": "Search", "structures": "Structures"}
        for label, name, _dim in STRUCTURE_FIELDS:
            self._tab_labels[name] = label
        for key in FEATURE_KEYS:
            if key != "structures":
                self._tab_labels[key] = FEATURE_LABELS[key]
        self._active_tab: str | None = None
        self._feature_vars: dict[str, tk.BooleanVar] = {
            key: tk.BooleanVar(value=False) for key in FEATURE_KEYS
        }
        self._startup_complete = False
        self._tab_load_overlay: TabLoadOverlay | None = None
        self._status_bar: ctk.CTkFrame | None = None
        self.version_var = tk.StringVar(value=DEFAULT_VERSION)

        self._startup_overlay = StartupOverlay(self, version=__version__)
        self._startup_steps: list[tuple[str, str]] = [
            ("Preparing layout…", "_startup_layout"),
            ("Loading version & features…", "_startup_version_features"),
            ("Loading structures…", "_startup_structures"),
            ("Loading search settings…", "_startup_search"),
            ("Loading controls…", "_startup_controls"),
            ("Loading criteria editor…", "_startup_criteria"),
            ("Loading results…", "_startup_results"),
            ("Finishing up…", "_startup_finish"),
        ]
        self._startup_index = 0
        self.update_idletasks()
        self.after(0, self._run_startup_step)

    def _run_startup_step(self) -> None:
        if self._startup_index >= len(self._startup_steps):
            return
        total = len(self._startup_steps)
        message, method_name = self._startup_steps[self._startup_index]
        self._startup_overlay.set_progress(self._startup_index / total, message)
        self._startup_overlay.lift()
        getattr(self, method_name)()
        self._startup_index += 1
        self._startup_overlay.set_progress(self._startup_index / total, message)
        self.update_idletasks()
        if self._startup_index < len(self._startup_steps):
            self.after(1, self._run_startup_step)
        else:
            self.after(1, self._complete_startup)

    def _complete_startup(self) -> None:
        self._startup_overlay.set_progress(0.95, "Applying defaults…")
        self._startup_overlay.lift()
        self._sync_gui_to_ezsf()
        self.update_idletasks()
        self.update()
        self._startup_overlay.set_progress(1.0, "Ready")
        self.update_idletasks()
        self.after(60, self._hide_startup_overlay)

    def _hide_startup_overlay(self) -> None:
        if self._startup_overlay.winfo_exists():
            self._startup_overlay.destroy()
        self._build_status_bar()
        self._startup_complete = True
        self.status_var.set("Ready")

    def _startup_layout(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.grid(row=0, column=0, sticky="nsew", padx=16, pady=(14, 12))
        self._body.grid_columnconfigure(0, weight=2, minsize=420)
        self._body.grid_columnconfigure(1, weight=3)
        self._body.grid_rowconfigure(0, weight=1)
        self._left_panel = ctk.CTkFrame(self._body, fg_color="transparent")
        self._left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._right_panel = ctk.CTkFrame(self._body, fg_color="transparent")
        self._right_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    def _startup_version_features(self) -> None:
        self._build_left_panel_header(self._left_panel)

    def _startup_structures(self) -> None:
        self._build_left_panel_tabs_shell(self._left_panel)
        self._build_structures_tab()

    def _startup_search(self) -> None:
        self._search_frame = ctk.CTkFrame(self._tab_stack_body, fg_color="transparent")
        self._tab_frames["search"] = self._search_frame
        self._build_search_tab(self._search_frame)

    def _startup_controls(self) -> None:
        self._build_left_panel_controls(self._left_panel)
        self._refresh_tabs()

    def _startup_criteria(self) -> None:
        self._right_panel.grid_rowconfigure(0, weight=2)
        self._right_panel.grid_rowconfigure(1, weight=3)
        self._right_panel.grid_columnconfigure(0, weight=1)
        self._build_right_panel_criteria(self._right_panel)

    def _startup_results(self) -> None:
        self._build_right_panel_results(self._right_panel)

    def _startup_finish(self) -> None:
        self._wire_ezsf_sync()

    def _load_tab_async(self, tab_key: str, builder) -> None:
        """Show tab loader, build on next event-loop tick, then reveal tab."""
        if self._tab_load_overlay is not None:
            self._tab_load_overlay.destroy()
        self._tab_load_overlay = TabLoadOverlay(self._tab_stack_body)
        self.update_idletasks()

        def _finish() -> None:
            try:
                builder()
            finally:
                if self._tab_load_overlay is not None:
                    self._tab_load_overlay.destroy()
                    self._tab_load_overlay = None
                if tab_key in self._tab_frames:
                    self._select_tab(tab_key)

        self.after(0, _finish)

    def _apply_style(self) -> None:
        pass

    def _build_ui(self) -> None:
        self._startup_layout()
        self._startup_version_features()
        self._startup_structures()
        self._startup_search()
        self._startup_controls()
        self._right_panel.grid_rowconfigure(0, weight=2)
        self._right_panel.grid_rowconfigure(1, weight=3)
        self._right_panel.grid_columnconfigure(0, weight=1)
        self._startup_criteria()
        self._startup_results()
        self._startup_finish()
        self._build_status_bar()
        self._sync_gui_to_ezsf()
        self._startup_complete = True

    def _build_left_panel_header(self, parent: ctk.CTkFrame) -> None:
        vf = card(parent)
        body = card_title(vf, "Minecraft Version")
        combo(
            body,
            values=VERSIONS,
            variable=self.version_var,
            height=34,
            state="readonly",
            fill=True,
        )

        ff = card(parent)
        fbody = card_title(ff, "Features")
        row1 = ctk.CTkFrame(fbody, fg_color="transparent")
        row1.pack(fill="x")
        row2 = ctk.CTkFrame(fbody, fg_color="transparent")
        row2.pack(fill="x", pady=(4, 0))
        for i, key in enumerate(FEATURE_KEYS):
            parent_row = row1 if i < 4 else row2
            ctk.CTkCheckBox(
                parent_row,
                text=FEATURE_LABELS[key],
                variable=self._feature_vars[key],
                command=lambda k=key: self._on_feature_toggled(k),
                font=("Ubuntu", 13),
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                border_color=COLORS["border"],
            ).pack(side="left", padx=(0, 12))

    def _build_left_panel_tabs_shell(self, parent: ctk.CTkFrame) -> None:
        self._tab_bar = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_subtle"],
        )
        self._tab_bar.pack(fill="x", pady=(4, 6))
        self._tab_bar_inner = ctk.CTkFrame(self._tab_bar, fg_color="transparent")
        self._tab_bar_inner.pack(fill="x", padx=6, pady=6)

        self._tab_stack = ctk.CTkFrame(
            parent,
            fg_color=COLORS["tab_body"],
            corner_radius=TAB_BODY_RADIUS,
            border_width=1,
            border_color=COLORS["border_subtle"],
        )
        self._tab_stack.pack(fill="both", expand=True, pady=(0, 8))
        self._tab_stack_body = ctk.CTkFrame(
            self._tab_stack,
            fg_color="transparent",
            corner_radius=max(6, TAB_BODY_RADIUS - TAB_BODY_INSET),
        )
        self._tab_stack_body.pack(fill="both", expand=True, padx=TAB_BODY_INSET, pady=TAB_BODY_INSET)

    def _build_left_panel_controls(self, parent: ctk.CTkFrame) -> None:
        bf = ctk.CTkFrame(parent, fg_color="transparent")
        bf.pack(fill="x", pady=(8, 4))
        self.start_btn = btn_primary(bf, "Start", self._start_search)
        self.start_btn.pack(side="left", padx=(0, 10))
        self.pause_btn = btn_secondary(bf, "Pause", self._toggle_pause)
        self.pause_btn.configure(state="disabled")
        self.pause_btn.pack(side="left", padx=(0, 10))
        self.stop_btn = btn_danger(bf, "Stop", self._stop_search)
        self.stop_btn.configure(state="disabled")
        self.stop_btn.pack(side="left")

    def _build_left_panel(self, parent: ctk.CTkFrame) -> None:
        self._build_left_panel_header(parent)
        self._build_left_panel_tabs_shell(parent)
        self._build_structures_tab()
        self._search_frame = ctk.CTkFrame(self._tab_stack_body, fg_color="transparent")
        self._tab_frames["search"] = self._search_frame
        self._build_search_tab(self._search_frame)
        self._build_left_panel_controls(parent)
        self._refresh_tabs()

    def _ensure_tab_button(self, key: str) -> None:
        if key in self._tab_buttons:
            return
        label = self._tab_labels.get(key, key)
        self._tab_buttons[key] = tab_button(
            self._tab_bar_inner,
            label,
            command=lambda k=key: self._select_tab(k),
        )

    def _select_tab(self, key: str) -> None:
        if key not in self._tab_frames:
            return
        self._active_tab = key
        for k, frame in self._tab_frames.items():
            if k == key:
                frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            else:
                frame.place_forget()
        for k, btn in self._tab_buttons.items():
            active = k == key
            btn.configure(
                fg_color=COLORS["tab_active"] if active else COLORS["surface"],
                border_width=2 if active else 1,
                border_color=COLORS["accent"] if active else COLORS["border"],
                text_color=COLORS["fg"] if active else COLORS["fg_muted"],
            )

    def _make_tab_host(self, key: str) -> ctk.CTkScrollableFrame:
        outer = ctk.CTkFrame(self._tab_stack_body, fg_color="transparent")
        self._tab_frames[key] = outer
        self._tab_hosts[key] = outer
        self._ensure_tab_button(key)
        return scrollable_tab(outer)

    def _current_tab_key(self) -> str | None:
        return self._active_tab

    def _tab_visible(self, key: str) -> bool:
        if key == "search":
            return True
        btn = self._tab_buttons.get(key)
        return btn is not None and btn.winfo_ismapped()

    def _visible_tab_keys(self) -> list[str]:
        keys: list[str] = []
        if self._feature_vars["structures"].get() and "structures" in self._tab_frames:
            keys.append("structures")
            for _label, name, _dim in STRUCTURE_FIELDS:
                if self._struct_enabled[name].get() and name in self._tab_frames:
                    keys.append(name)
        for key in FEATURE_KEYS:
            if key == "structures":
                continue
            if self._feature_vars[key].get() and key in self._tab_frames:
                keys.append(key)
        keys.append("search")
        return keys

    def _refresh_tabs(self, select: str | None = None) -> None:
        stay_on = None if select else self._current_tab_key()
        visible = self._visible_tab_keys()
        for key in visible:
            self._ensure_tab_button(key)
        for key, btn in self._tab_buttons.items():
            if key in visible:
                btn.pack(side="left", padx=(0, 6))
            else:
                btn.pack_forget()
        target = select
        if target and target in visible:
            self._select_tab(target)
        elif stay_on and stay_on in visible:
            self._select_tab(stay_on)
        elif visible:
            self._select_tab(visible[0])

    def _select_tab_key(self, key: str) -> None:
        self._select_tab(key)

    def _ensure_feature_tab(self, key: str) -> None:
        if key in self._feature_built or key == "structures":
            return
        builders = {
            "spawn": self._build_spawn_tab,
            "biomes": self._build_biomes_tab,
            "terrain": self._build_terrain_tab,
            "loot": self._build_mobs_tab,
        }
        builder = builders.get(key)
        if builder is None:
            return
        self._feature_built.add(key)
        builder()

    def _ensure_struct_tab(self, name: str) -> None:
        if name in self._struct_built:
            return
        self._struct_built.add(name)
        self._build_single_struct_tab(name)

    def _ensure_tabs_for_criteria(self, criteria: dict[str, Any], features: set[str]) -> None:
        for key in features:
            if key != "structures":
                self._ensure_feature_tab(key)
        for struct in criteria.get("structures") or []:
            self._ensure_struct_tab(struct["name"])
        if (criteria.get("ruined_portal") or {}).get("enabled"):
            self._ensure_struct_tab("ruined_portal")
        if (criteria.get("bastion") or {}).get("enabled"):
            self._ensure_struct_tab("bastion")

    def _on_feature_toggled(self, key: str) -> None:
        if not self._startup_complete or self._syncing:
            return
        enabled = self._feature_vars[key].get()
        if enabled and key != "structures" and key not in self._feature_built:
            self._refresh_tabs(select=key)
            self._load_tab_async(key, lambda k=key: self._ensure_feature_tab(k))
            return
        select = key if enabled else None
        self._refresh_tabs(select=select)

    def _on_structure_toggled(self, name: str) -> None:
        if not self._startup_complete or self._syncing:
            return
        enabled = self._struct_enabled[name].get()
        if enabled and name not in self._struct_built:
            if any(v.get() for v in self._struct_enabled.values()):
                self._feature_vars["structures"].set(True)
            self._refresh_tabs(select=name)
            self._load_tab_async(name, lambda n=name: self._ensure_struct_tab(n))
            return
        if any(v.get() for v in self._struct_enabled.values()):
            self._feature_vars["structures"].set(True)
        select = name if enabled else None
        self._refresh_tabs(select=select)

    def _build_structures_tab(self) -> None:
        tab = self._make_tab_host("structures")
        heading(tab, "Select structures — each opens its own config tab").pack(
            anchor="w", pady=(0, 8)
        )
        picker = ctk.CTkFrame(tab, fg_color="transparent")
        picker.pack(fill="x")

        col_a = ctk.CTkFrame(picker, fg_color="transparent")
        col_b = ctk.CTkFrame(picker, fg_color="transparent")
        col_a.pack(side="left", fill="both", expand=True)
        col_b.pack(side="left", fill="both", expand=True)

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

    def _make_struct_tab_host(self, name: str) -> ctk.CTkScrollableFrame:
        outer = ctk.CTkFrame(self._tab_stack_body, fg_color="transparent")
        self._struct_tab_hosts[name] = outer
        self._tab_frames[name] = outer
        self._ensure_tab_button(name)
        return scrollable_tab(outer)

    def _build_single_struct_tab(self, name: str) -> None:
        for label, struct_name, dim in STRUCTURE_FIELDS:
            if struct_name != name:
                continue
            tab = self._make_struct_tab_host(name)
            kind = structure_kind(name)
            cfg: dict[str, Any] = {"kind": kind, "dimension": dim, "label": label}

            if kind == "portal":
                cfg["dimension_var"] = labeled_combo(tab, "Dimension", ("overworld", "nether"), dim)
                cfg["ref"] = ref_row(tab, "spawn")
                cfg["max_dist"] = dist_row(tab, default_dist(name))
                cfg["viable"] = tk.BooleanVar(value=True)
                checkbox(tab, "Must be viable", cfg["viable"])
                heading(tab, "Variant").pack(anchor="w", pady=(8, 2))
                cfg["giant"] = labeled_combo(tab, "Giant portal", ("", "false", "true"), "false")
                cfg["template"] = labeled_combo(tab, "Template (1–10)", PORTAL_TEMPLATES, "6")
                cfg["underground"] = labeled_combo(tab, "Underground", ("", "false", "true"), "")
                cfg["airpocket"] = labeled_combo(tab, "Air pocket", ("", "false", "true"), "")
                heading(tab, "Frame (after crying obsidian)").pack(anchor="w", pady=(8, 2))
                cfg["top_missing"] = labeled_entry(tab, "Top row missing", "1")
                cfg["frame_missing"] = labeled_entry(tab, "Total frame missing", "1")
                muted(tab, "portal_6 = 5×5 frame, 1 missing at top center").pack(anchor="w")
                heading(tab, "Chest loot requirements").pack(anchor="w", pady=(8, 2))
                loot_label = muted(tab, "")
                cfg["loot_table_label"] = loot_label
                cfg["chest_frame"] = ctk.CTkFrame(tab, fg_color="transparent")
                cfg["chest_frame"].pack(fill="x")
                self._struct_configs[name] = cfg
                self._chest_rows[name] = []
                btn_secondary(tab, "+ Add chest item", command=lambda n=name: self._add_chest_row(n)).pack(
                    anchor="w", pady=4
                )
                self._add_chest_row(name, "obsidian", "1")
                self._add_chest_row(name, "flint_and_steel", "1")
                self._wire_struct_config(name)
                return

            if kind == "bastion":
                cfg["variant"] = labeled_combo(tab, "Variant", BASTION_VARIANTS, "treasure")
                cfg["ref"] = ref_row(tab, "0,0")
                cfg["max_dist"] = dist_row(tab, default_dist(name))
                cfg["viable"] = tk.BooleanVar(value=True)
                checkbox(tab, "Must be viable", cfg["viable"])

            elif kind == "loot_chest":
                table = STRUCTURE_LOOT_TABLE[name]
                cfg["loot_table"] = table
                self._struct_configs[name] = cfg
                loot_label = heading(tab, "")
                loot_label.pack(anchor="w", pady=(0, 6))
                cfg["loot_table_label"] = loot_label
                cfg["ref"] = ref_row(tab, "spawn")
                cfg["max_dist"] = dist_row(tab, default_dist(name))
                cfg["viable"] = tk.BooleanVar(value=True)
                checkbox(tab, "Must be viable", cfg["viable"])
                heading(tab, "Chest loot requirements").pack(anchor="w", pady=(8, 2))
                cfg["chest_frame"] = ctk.CTkFrame(tab, fg_color="transparent")
                cfg["chest_frame"].pack(fill="x")
                btn_secondary(tab, "+ Add chest item", command=lambda n=name: self._add_chest_row(n)).pack(
                    anchor="w", pady=4
                )
                self._chest_rows[name] = []
                default_items = {
                    "treasure": "heart_of_the_sea",
                    "shipwreck": "gold_ingot",
                    "desert_pyramid": "diamond",
                    "jungle_temple": "diamond",
                    "ancient_city": "diamond",
                    "trail_ruin": "iron_ingot",
                }
                default_item = default_items.get(name, "gold_ingot")
                self._add_chest_row(name, default_item, "1")
                self._wire_struct_config(name)
                self._refresh_loot_ui()
                return

            else:
                cfg["ref"] = ref_row(tab, "spawn")
                cfg["max_dist"] = dist_row(tab, default_dist(name))
                cfg["viable"] = tk.BooleanVar(value=True)
                checkbox(tab, "Must be viable", cfg["viable"])
                if name == "village":
                    cfg["abandoned"] = labeled_combo(tab, "Abandoned village", ("", "false", "true"), "")

            self._struct_configs[name] = cfg
            self._wire_struct_config(name)
            return

    def _build_structure_config_tabs(self) -> None:
        for _label, name, _dim in STRUCTURE_FIELDS:
            self._ensure_struct_tab(name)

    def _loot_table_for_struct(self, struct_name: str) -> str | None:
        kind = structure_kind(struct_name)
        if kind == "portal":
            return "ruined_portal"
        if kind == "loot_chest":
            return STRUCTURE_LOOT_TABLE.get(struct_name)
        return None

    def _loot_items_for_struct(self, struct_name: str) -> tuple[str, ...]:
        table = self._loot_table_for_struct(struct_name)
        if table is None:
            return DEFAULT_LOOT_ITEMS
        items = loot_table_item_names(self.version_var.get(), table)
        return items if items else DEFAULT_LOOT_ITEMS

    def _refresh_loot_ui(self, *_args: object) -> None:
        version = self.version_var.get()
        try:
            data_ver = loot_data_version(version)
        except FileNotFoundError:
            data_ver = version
        for name, cfg in self._struct_configs.items():
            table = self._loot_table_for_struct(name)
            if table is None:
                continue
            label = cfg.get("loot_table_label")
            if label is not None:
                label.configure(text=f"Loot table: {table} ({data_ver})")
            items = self._loot_items_for_struct(name)
            for row in self._chest_rows.get(name, []):
                combo = row.get("combo")
                if combo is None:
                    continue
                combo.configure(values=list(items))
                current = row["item"].get()
                if current not in items and items:
                    row["item"].set(items[0])

    def _add_chest_row(self, struct_name: str, item: str = "obsidian", count: str = "1") -> None:
        cfg = self._struct_configs[struct_name]
        frame = cfg["chest_frame"]
        row = chest_item_row(frame, self._loot_items_for_struct(struct_name))

        def remove() -> None:
            row["row"].destroy()
            self._chest_rows[struct_name].remove(row)
            self._schedule_gui_to_ezsf()

        mini_btn(row["row"], "−", remove, width=32).pack(side="right", padx=(4, 0))
        row["item"].set(item)
        row["count"].set(count)
        self._chest_rows[struct_name].append(row)
        self._trace_gui_sync(row["item"])
        self._trace_gui_sync(row["count"])

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
        muted(body, "Use | for multiple, e.g. plains | forest").pack(anchor="w")

        body, self.stronghold_require = toggle_block(tab, "Stronghold requirements")
        self.sh_nearest_enabled = tk.BooleanVar(value=False)
        checkbox(body, "Nearest stronghold within", self.sh_nearest_enabled)
        self.sh_nearest_dist = dist_row(body, "1500")
        self.sh_nearest_ref = ref_row(body, "spawn")
        self.sh_under_spawn = tk.BooleanVar(value=False)
        self.sh_full = tk.BooleanVar(value=False)
        checkbox(body, "Under spawn (~250 blocks)", self.sh_under_spawn)
        checkbox(body, "Full stronghold (ring-1 heuristic, approximate)", self.sh_full)
        self.sh_ring_enabled = tk.BooleanVar(value=False)
        checkbox(body, "Specific ring", self.sh_ring_enabled)
        self.sh_ring = labeled_entry(body, "Ring number", "1")
        self.sh_max_angle_enabled = tk.BooleanVar(value=False)
        checkbox(body, "Max angle from spawn to ring-1 SH (degrees from +Z)", self.sh_max_angle_enabled)
        self.sh_max_angle = labeled_entry(body, "Max angle (degrees)", "90")
        muted(
            body,
            "Stronghold rules: ring/angle are exact from cubiomes; "
            "'under spawn' and 'full' are heuristics (see README).",
        ).pack(anchor="w", pady=(4, 0))
        self._wire_spawn_sync()

    def _build_biomes_tab(self) -> None:
        tab = self._make_tab_host("biomes")

        body, self.biome_at_require = toggle_block(tab, "Biome at coordinates")
        self.biome_at_dim = labeled_combo(body, "Dimension", DIMENSIONS, "overworld")
        self.biome_at_x = labeled_entry(body, "X", "0")
        self.biome_at_y = labeled_entry(body, "Y", "64")
        self.biome_at_z = labeled_entry(body, "Z", "0")
        self.biome_at_names = labeled_entry(body, "Biome(s)", "plains | forest", 20)
        self.biome_at_negate = tk.BooleanVar(value=False)
        checkbox(body, "Exclude these biomes (not)", self.biome_at_negate)

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
        self._wire_biomes_sync()

    def _build_terrain_tab(self) -> None:
        tab = self._make_tab_host("terrain")

        body, self.terrain_require = toggle_block(tab, "Terrain predicate (experimental)")
        muted(body, "Uses biome sampling as a terrain proxy — not true height/noise.").pack(
            anchor="w", pady=(0, 4)
        )
        self.terrain_dim = labeled_combo(body, "Dimension", DIMENSIONS, "overworld")
        self.terrain_x = labeled_entry(body, "X", "0")
        self.terrain_z = labeled_entry(body, "Z", "0")
        self.terrain_radius = labeled_entry(body, "Radius", "128")
        self.terrain_pred = labeled_combo(body, "Type", TERRAIN_TYPES, "flat")
        self.terrain_negate = tk.BooleanVar(value=False)
        checkbox(body, "Invert (not)", self.terrain_negate)

        body, self.height_require = toggle_block(tab, "Height at coordinates (experimental)")
        muted(body, "Overworld/nether height is approximated (Y=64); end uses cubiomes surface.").pack(
            anchor="w", pady=(0, 4)
        )
        self.height_dim = labeled_combo(body, "Dimension", DIMENSIONS, "overworld")
        self.height_x = labeled_entry(body, "X", "0")
        self.height_z = labeled_entry(body, "Z", "0")
        self.height_op = labeled_combo(body, "Operator", COMPARE_OPS, ">=")
        self.height_value = labeled_entry(body, "Y value", "64")
        self._wire_terrain_sync()

    def _build_mobs_tab(self) -> None:
        tab = self._make_tab_host("loot")

        self.mob_type = labeled_combo(tab, "Mob", MOB_TYPES, "witch")
        self.mob_dim = labeled_combo(tab, "Dimension", DIMENSIONS, "overworld")
        self.mob_ref = ref_row(tab, "spawn")
        self.mob_dist = dist_row(tab, "200")
        self.mob_biomes = labeled_entry(tab, "Biome(s)", "swamp", 20)
        muted(tab, "Use | for multiple biomes, e.g. swamp | mangrove_swamp").pack(anchor="w")
        self._wire_mobs_sync()

    def _build_search_tab(self, tab: ctk.CTkFrame) -> None:
        scroll = scrollable_tab(tab)

        sf = card(scroll)
        sbody = card_title(sf, "Search settings")
        self.max_results_var = labeled_entry(sbody, "Max results", "10")
        self.threads_var = labeled_entry(sbody, "Threads (0=auto)", "0")
        self.random_var = tk.BooleanVar(value=True)
        checkbox(sbody, "Random search", self.random_var)
        self.seed_start_var = labeled_entry(sbody, "Seed start (optional)", "")
        self.seed_end_var = labeled_entry(sbody, "Seed end (optional)", "")

        vf = card(scroll)
        vbody = card_title(vf, "Verify seed")
        vrow = ctk.CTkFrame(vbody, fg_color="transparent")
        vrow.pack(fill="x")
        self.verify_seed_var = tk.StringVar(value="")
        ctk.CTkEntry(
            vrow,
            textvariable=self.verify_seed_var,
            width=200,
            height=32,
            corner_radius=8,
            fg_color=COLORS["input"],
            font=("Ubuntu", 13),
        ).pack(side="left", padx=(0, 8))
        btn_secondary(vrow, "Check seed", self._verify_seed).pack(side="left")

        lf = card(scroll)
        lbody = card_title(lf, "Quick distance filters (legacy)")
        muted(lbody, "Also checked directly (no .ezsf needed)").pack(anchor="w", pady=(0, 4))
        self.dist_vars: dict[str, tk.StringVar] = {}
        self.dist_enabled: dict[str, tk.BooleanVar] = {}
        self.dist_entries: dict[str, ctk.CTkEntry] = {}
        legacy = [
            ("Village", "village_dist"),
            ("Ruined portal", "ruined_portal_dist"),
            ("Stronghold", "stronghold_dist"),
            ("Bastion", "bastion_dist"),
            ("Fortress", "fortress_dist"),
        ]
        for label, key in legacy:
            row = ctk.CTkFrame(lbody, fg_color="transparent")
            row.pack(fill="x", pady=2)
            enabled = tk.BooleanVar(value=False)
            self.dist_enabled[key] = enabled
            ctk.CTkCheckBox(
                row,
                text="",
                variable=enabled,
                width=24,
                fg_color=COLORS["accent"],
            ).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(row, text=label, width=140, anchor="w", font=("Ubuntu", 13)).pack(side="left")
            var = tk.StringVar(value="500" if key == "village_dist" else "0")
            self.dist_vars[key] = var
            entry = ctk.CTkEntry(
                row,
                textvariable=var,
                width=80,
                height=32,
                corner_radius=8,
                fg_color=COLORS["input"],
                font=("Ubuntu", 13),
            )
            entry.pack(side="right")
            self.dist_entries[key] = entry
            enabled.trace_add("write", lambda *_a, k=key: self._toggle_dist_field(k))
            self._toggle_dist_field(key)

        self.stronghold_under = tk.BooleanVar(value=False)
        self.stronghold_full = tk.BooleanVar(value=False)
        self.spawn_dist_enabled = tk.BooleanVar(value=False)
        self.spawn_dist_var = tk.StringVar(value="0")
        self.spawn_biome_enabled = tk.BooleanVar(value=False)
        self.spawn_biome_var = tk.StringVar(value="")

    def _build_right_panel_criteria(self, parent: ctk.CTkFrame) -> None:
        ef = card(parent, pack=False)
        ef.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        ebody = card_title(ef, ".ezsf Criteria (text)")

        toolbar = ctk.CTkFrame(ebody, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 8))
        btn_secondary(toolbar, "Load .ezsf", self._load_ezsf).pack(side="left", padx=(0, 10))
        btn_secondary(toolbar, "Save .ezsf", self._save_ezsf).pack(side="left", padx=(0, 10))
        preset_names = [label for label, _file in PRESETS]
        self.preset_var = tk.StringVar(value=preset_names[0] if preset_names else "")
        combo(
            toolbar,
            values=preset_names,
            variable=self.preset_var,
            width=220,
            state="readonly",
        ).pack(side="left", padx=(0, 10))
        btn_secondary(toolbar, "Load preset", self._load_preset).pack(side="left")

        self.ezsf_text = textbox(ebody, height=220, wrap="none", monospace=True)
        self.ezsf_text.pack(fill="both", expand=True)

    def _build_right_panel_results(self, parent: ctk.CTkFrame) -> None:
        rf = card(parent, pack=False)
        rf.grid(row=1, column=0, sticky="nsew", pady=(0, 4))
        rbody = card_title(rf, "Results")

        rtoolbar = ctk.CTkFrame(rbody, fg_color="transparent")
        rtoolbar.pack(fill="x", pady=(0, 8))
        btn_secondary(rtoolbar, "Export TXT", lambda: self._export_results("txt")).pack(side="left", padx=(0, 10))
        btn_secondary(rtoolbar, "Export JSON", lambda: self._export_results("json")).pack(side="left")

        rsplit = ctk.CTkFrame(rbody, fg_color="transparent")
        rsplit.pack(fill="both", expand=True)
        rsplit.grid_rowconfigure(0, weight=2)
        rsplit.grid_rowconfigure(1, weight=1)
        rsplit.grid_columnconfigure(0, weight=1)

        tree_wrap = ctk.CTkFrame(rsplit, fg_color="transparent")
        tree_wrap.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        cols = ("seed", "spawn", "summary")
        self.results_tree, _tree_host = embed_treeview(tree_wrap, cols)
        self.results_tree.heading("seed", text="Seed")
        self.results_tree.heading("spawn", text="Spawn")
        self.results_tree.heading("summary", text="Summary")
        self.results_tree.column("seed", width=180)
        self.results_tree.column("spawn", width=120)
        self.results_tree.column("summary", width=420)

        detail_card = ctk.CTkFrame(
            rsplit,
            fg_color=COLORS["code"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_subtle"],
        )
        detail_card.grid(row=1, column=0, sticky="nsew")
        ctk.CTkLabel(
            detail_card,
            text="Result details",
            font=("Ubuntu", 14, "bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 4))
        self.result_detail_text = textbox(detail_card, height=140, wrap="word", monospace=True)
        self.result_detail_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.result_detail_text.configure(state="disabled")

        self.results_tree.bind("<<TreeviewSelect>>", self._on_result_select)
        self.results_tree.bind("<Double-1>", self._copy_seed)
        muted(rbody, "Select a row for details; double-click to copy seed").pack(anchor="w", pady=(8, 4))

    def _build_right_panel(self, parent: ctk.CTkFrame) -> None:
        parent.grid_rowconfigure(0, weight=2)
        parent.grid_rowconfigure(1, weight=3)
        parent.grid_columnconfigure(0, weight=1)
        self._build_right_panel_criteria(parent)
        self._build_right_panel_results(parent)

    def _build_status_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=0, height=40)
        bar.grid(row=1, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)
        self._status_bar = bar

        self.status_var = tk.StringVar(value="Ready")
        ctk.CTkLabel(
            bar,
            textvariable=self.status_var,
            font=("Ubuntu", 12),
            text_color=COLORS["fg_muted"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=8)

        self.progress = IndeterminateProgressBar(bar, width=180, height=10)
        self.progress.grid(row=0, column=1, sticky="e", padx=(0, 16), pady=8)
        self.progress.grid_remove()

    def _toggle_dist_field(self, key: str) -> None:
        entry = self.dist_entries.get(key)
        if entry is None:
            return
        entry.configure(state="normal" if self.dist_enabled[key].get() else "disabled")

    def _trace_gui_sync(self, var: tk.Variable) -> None:
        var.trace_add("write", self._schedule_gui_to_ezsf)

    def _trace_ref_row(self, ref: dict[str, Any]) -> None:
        self._trace_gui_sync(ref["ref"])
        self._trace_gui_sync(ref["custom"])

    def _trace_struct_config(self, cfg: dict[str, Any]) -> None:
        for val in cfg.values():
            if isinstance(val, tk.Variable):
                self._trace_gui_sync(val)
            elif isinstance(val, dict) and "ref" in val and "custom" in val:
                self._trace_ref_row(val)

    def _wire_struct_config(self, name: str) -> None:
        cfg = self._struct_configs.get(name)
        if cfg is None:
            return
        self._trace_struct_config(cfg)
        for row in self._chest_rows.get(name, []):
            self._trace_gui_sync(row["item"])
            self._trace_gui_sync(row["count"])

    def _wire_spawn_sync(self) -> None:
        self._trace_ref_row(self.spawn_ref)
        self._trace_gui_sync(self.spawn_max_dist)
        self._trace_gui_sync(self.spawn_biomes)
        self._trace_gui_sync(self.spawn_require_dist)
        self._trace_gui_sync(self.stronghold_require)
        self._trace_gui_sync(self.sh_nearest_enabled)
        self._trace_ref_row(self.sh_nearest_ref)
        self._trace_gui_sync(self.sh_nearest_dist)
        self._trace_gui_sync(self.sh_under_spawn)
        self._trace_gui_sync(self.sh_full)
        self._trace_gui_sync(self.sh_ring_enabled)
        self._trace_gui_sync(self.sh_ring)
        self._trace_gui_sync(self.sh_max_angle_enabled)
        self._trace_gui_sync(self.sh_max_angle)

    def _wire_biomes_sync(self) -> None:
        self._trace_gui_sync(self.biome_at_require)
        self._trace_gui_sync(self.biome_at_dim)
        self._trace_gui_sync(self.biome_at_x)
        self._trace_gui_sync(self.biome_at_y)
        self._trace_gui_sync(self.biome_at_z)
        self._trace_gui_sync(self.biome_at_names)
        self._trace_gui_sync(self.biome_at_negate)
        self._trace_gui_sync(self.biome_region_require)
        self._trace_gui_sync(self.biome_region_dim)
        self._trace_gui_sync(self.biome_region_x1)
        self._trace_gui_sync(self.biome_region_z1)
        self._trace_gui_sync(self.biome_region_x2)
        self._trace_gui_sync(self.biome_region_z2)
        self._trace_gui_sync(self.biome_region_y)
        self._trace_gui_sync(self.biome_region_op)
        self._trace_gui_sync(self.biome_region_biome)
        self._trace_gui_sync(self.biome_region_pct)

    def _wire_terrain_sync(self) -> None:
        self._trace_gui_sync(self.terrain_require)
        self._trace_gui_sync(self.terrain_dim)
        self._trace_gui_sync(self.terrain_x)
        self._trace_gui_sync(self.terrain_z)
        self._trace_gui_sync(self.terrain_radius)
        self._trace_gui_sync(self.terrain_pred)
        self._trace_gui_sync(self.terrain_negate)
        self._trace_gui_sync(self.height_require)
        self._trace_gui_sync(self.height_dim)
        self._trace_gui_sync(self.height_x)
        self._trace_gui_sync(self.height_z)
        self._trace_gui_sync(self.height_op)
        self._trace_gui_sync(self.height_value)

    def _wire_mobs_sync(self) -> None:
        self._trace_gui_sync(self.mob_type)
        self._trace_gui_sync(self.mob_dim)
        self._trace_ref_row(self.mob_ref)
        self._trace_gui_sync(self.mob_dist)
        self._trace_gui_sync(self.mob_biomes)

    def _wire_ezsf_sync(self) -> None:
        self._trace_gui_sync(self.version_var)
        for var in self._feature_vars.values():
            self._trace_gui_sync(var)
        for var in self._struct_enabled.values():
            self._trace_gui_sync(var)

        self._trace_gui_sync(self.struct_between_enabled)
        self._trace_gui_sync(self.struct_between_a)
        self._trace_gui_sync(self.struct_between_b)
        self._trace_gui_sync(self.struct_between_dim)
        self._trace_ref_row(self.struct_between_ref)
        self._trace_gui_sync(self.struct_between_dist)

        self._trace_gui_sync(self.dist_rule_enabled)
        self._trace_gui_sync(self.dist_rule_a)
        self._trace_gui_sync(self.dist_rule_b)
        self._trace_gui_sync(self.dist_rule_op)
        self._trace_gui_sync(self.dist_rule_value)
        self._trace_gui_sync(self.dist_rule_dim)

        self._trace_gui_sync(self.max_results_var)
        self._trace_gui_sync(self.threads_var)
        self._trace_gui_sync(self.random_var)
        self._trace_gui_sync(self.seed_start_var)
        self._trace_gui_sync(self.seed_end_var)
        for var in self.dist_vars.values():
            self._trace_gui_sync(var)
        for var in self.dist_enabled.values():
            self._trace_gui_sync(var)
        self._trace_gui_sync(self.stronghold_under)
        self._trace_gui_sync(self.stronghold_full)
        self._trace_gui_sync(self.spawn_dist_enabled)
        self._trace_gui_sync(self.spawn_dist_var)
        self._trace_gui_sync(self.spawn_biome_enabled)
        self._trace_gui_sync(self.spawn_biome_var)

        def on_ezsf_modified(_event: object = None) -> None:
            if self._syncing:
                return
            self._schedule_ezsf_to_gui()

        self.ezsf_text.bind("<KeyRelease>", on_ezsf_modified)
        self.ezsf_text.bind("<FocusOut>", lambda _e: self._schedule_ezsf_to_gui())
        self.version_var.trace_add("write", self._refresh_loot_ui)

    def _ezsf_editor_focused(self) -> bool:
        try:
            focus = self.focus_get()
        except (KeyError, tk.TclError):
            # ttk.Combobox popdown focus isn't a normal widget path on some platforms
            return False
        widget: tk.Misc | None = focus
        while widget is not None:
            if widget == self.ezsf_text:
                return True
            widget = widget.master if hasattr(widget, "master") else None
        return False

    def _text_get(self, widget: ctk.CTkTextbox) -> str:
        return widget.get("1.0", "end").strip()

    def _text_set(self, widget: ctk.CTkTextbox, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        if widget is self.result_detail_text:
            widget.configure(state="disabled")

    def _text_clear(self, widget: ctk.CTkTextbox, *, disabled: bool = False) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        if disabled:
            widget.configure(state="disabled")

    def _progress_start(self) -> None:
        self.progress.grid()
        self.progress.start()

    def _progress_stop(self) -> None:
        self.progress.stop()
        self.progress.grid_remove()

    def _schedule_gui_to_ezsf(self, *_args: object) -> None:
        if self._syncing or self._ezsf_editor_focused():
            return
        if self._gui_to_ezsf_after is not None:
            self.after_cancel(self._gui_to_ezsf_after)
        self._gui_to_ezsf_after = self.after(120, self._sync_gui_to_ezsf)

    def _schedule_ezsf_to_gui(self) -> None:
        if self._syncing:
            return
        if self._ezsf_to_gui_after is not None:
            self.after_cancel(self._ezsf_to_gui_after)
        self._ezsf_to_gui_after = self.after(250, self._debounced_ezsf_to_gui)

    def _sync_gui_to_ezsf(self) -> None:
        self._gui_to_ezsf_after = None
        if self._syncing:
            return
        if self._ezsf_to_gui_after is not None:
            self.after_cancel(self._ezsf_to_gui_after)
            self._ezsf_to_gui_after = None
        self._syncing = True
        try:
            criteria = self._collect_gui_criteria()
            criteria["emit_version"] = True
            text = build_ezsf(criteria, version=self.version_var.get())
            self._text_set(self.ezsf_text, text)
        finally:
            self._syncing = False

    def _debounced_ezsf_to_gui(self) -> None:
        self._ezsf_to_gui_after = None
        if self._gui_to_ezsf_after is not None:
            self.after_cancel(self._gui_to_ezsf_after)
            self._gui_to_ezsf_after = None
        text = self._text_get(self.ezsf_text)
        if not text:
            return
        self._syncing = True
        try:
            criteria, features, doc = parse_ezsf_to_criteria(text)
            if doc.version:
                self.version_var.set(doc.version)
            apply_criteria_to_gui(self, criteria, features)
        except Exception:
            pass
        finally:
            self._syncing = False

    def _current_ezsf_text(self) -> str:
        return self._text_get(self.ezsf_text)

    def _collect_gui_criteria(self) -> dict[str, Any]:
        for key in FEATURE_KEYS:
            if key != "structures" and self._feature_vars[key].get():
                self._ensure_feature_tab(key)
        structures: list[dict[str, Any]] = []
        loot_rules: list[dict[str, Any]] = []
        ruined_portal: dict[str, Any] = {"enabled": False}
        bastion: dict[str, Any] = {"enabled": False}

        for label, name, dim in STRUCTURE_FIELDS:
            if not self._struct_enabled[name].get():
                continue
            self._ensure_struct_tab(name)
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
                entry = {
                    "enabled": True,
                    "name": name,
                    "dimension": dim,
                    "ref": ref,
                    "ref_pos": ref_pos,
                    "max_dist": cfg["max_dist"].get(),
                    "viable": cfg["viable"].get(),
                }
                if name == "village" and "abandoned" in cfg:
                    abandoned = cfg["abandoned"].get().strip()
                    if abandoned:
                        entry["abandoned"] = abandoned
                structures.append(entry)

        if "spawn" in self._feature_built:
            s_ref, s_ref_pos = resolve_ref(self.spawn_ref)
            sh_ref, sh_ref_pos = resolve_ref(self.sh_nearest_ref)
            spawn_block = {
                "enabled": self.spawn_require_dist.get(),
                "ref": s_ref,
                "ref_pos": s_ref_pos,
                "max_dist": self.spawn_max_dist.get(),
                "biomes": self.spawn_biomes.get(),
            }
            stronghold_block = {
                "enabled": self.stronghold_require.get(),
                "nearest_enabled": self.sh_nearest_enabled.get(),
                "nearest_dist": self.sh_nearest_dist.get(),
                "nearest_ref": sh_ref,
                "nearest_ref_pos": sh_ref_pos,
                "under_spawn": self.sh_under_spawn.get(),
                "full": self.sh_full.get(),
                "ring": self.sh_ring.get() if self.sh_ring_enabled.get() else None,
                "max_angle": self.sh_max_angle.get() if self.sh_max_angle_enabled.get() else None,
            }
        else:
            spawn_block = {
                "enabled": False,
                "ref": "origin",
                "ref_pos": None,
                "max_dist": "0",
                "biomes": "",
            }
            stronghold_block = {
                "enabled": False,
                "nearest_enabled": False,
                "nearest_dist": "1500",
                "nearest_ref": "spawn",
                "nearest_ref_pos": None,
                "under_spawn": False,
                "full": False,
                "ring": None,
                "max_angle": None,
            }

        if "biomes" in self._feature_built:
            biomes_block = [
                {
                    "enabled": self.biome_at_require.get(),
                    "dimension": self.biome_at_dim.get(),
                    "x": self.biome_at_x.get(),
                    "y": self.biome_at_y.get(),
                    "z": self.biome_at_z.get(),
                    "names": self.biome_at_names.get(),
                    "negate": self.biome_at_negate.get(),
                }
            ]
            biome_regions_block = [
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
            ]
        else:
            biomes_block = [{"enabled": False}]
            biome_regions_block = [{"enabled": False}]

        if "terrain" in self._feature_built:
            terrain_block = [
                {
                    "enabled": self.terrain_require.get(),
                    "dimension": self.terrain_dim.get(),
                    "x": self.terrain_x.get(),
                    "z": self.terrain_z.get(),
                    "radius": self.terrain_radius.get(),
                    "predicate": self.terrain_pred.get(),
                    "negate": self.terrain_negate.get(),
                }
            ]
            heights_block = [
                {
                    "enabled": self.height_require.get(),
                    "dimension": self.height_dim.get(),
                    "x": self.height_x.get(),
                    "z": self.height_z.get(),
                    "op": self.height_op.get(),
                    "value": self.height_value.get(),
                }
            ]
        else:
            terrain_block = [{"enabled": False}]
            heights_block = [{"enabled": False}]

        if "loot" in self._feature_built:
            mob_ref, mob_ref_pos = resolve_ref(self.mob_ref)
            mobs_block = [
                {
                    "enabled": self._feature_vars["loot"].get(),
                    "mob": self.mob_type.get(),
                    "dimension": self.mob_dim.get(),
                    "ref": mob_ref,
                    "ref_pos": mob_ref_pos,
                    "max_dist": self.mob_dist.get(),
                    "biomes": self.mob_biomes.get(),
                }
            ]
        else:
            mobs_block = [{"enabled": False}]

        return {
            "emit_version": False,
            "threads": self.threads_var.get(),
            "max_results": self.max_results_var.get(),
            "seed_start": self.seed_start_var.get().strip() or None,
            "seed_end": self.seed_end_var.get().strip() or None,
            "random_search": self.random_var.get(),
            "spawn": spawn_block,
            "stronghold": stronghold_block,
            "structures": structures,
            "ruined_portal": ruined_portal,
            "bastion": bastion,
            "biomes": biomes_block,
            "biome_regions": biome_regions_block,
            "terrain": terrain_block,
            "heights": heights_block,
            "loot": loot_rules,
            "mobs": mobs_block,
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

    def _set_ezsf_content(self, text: str) -> None:
        if self._gui_to_ezsf_after is not None:
            self.after_cancel(self._gui_to_ezsf_after)
            self._gui_to_ezsf_after = None
        if self._ezsf_to_gui_after is not None:
            self.after_cancel(self._ezsf_to_gui_after)
            self._ezsf_to_gui_after = None
        self._syncing = True
        try:
            self._text_set(self.ezsf_text, text)
        finally:
            self._syncing = False
        self._debounced_ezsf_to_gui()

    def _load_preset(self) -> None:
        label = self.preset_var.get()
        for preset_label, filename in PRESETS:
            if preset_label == label:
                path = examples_dir() / filename
                if path.is_file():
                    with open(path, encoding="utf-8") as f:
                        self._set_ezsf_content(f.read())
                    self.status_var.set(f"Loaded preset: {preset_label}")
                else:
                    messagebox.showwarning("Preset", f"Not found: {path}")
                return

    def _load_example(self) -> None:
        self._load_preset()

    def _load_ruined_portal_example(self) -> None:
        self.preset_var.set(PRESETS[0][0])
        self._load_preset()

    def _load_speedrun_example(self) -> None:
        self.preset_var.set(PRESETS[1][0])
        self._load_preset()

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

    def _load_ezsf(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("EZ Seed Finder", "*.ezsf"), ("All files", "*.*")]
        )
        if path:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            self._set_ezsf_content(content)
            self.status_var.set(f"Loaded {os.path.basename(path)}")

    def _save_ezsf(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".ezsf",
            filetypes=[("EZ Seed Finder", "*.ezsf")],
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._current_ezsf_text())
            self.status_var.set(f"Saved {os.path.basename(path)}")

    def _var_get(self, attr: str, default: Any = False) -> Any:
        if not hasattr(self, attr):
            return default
        return getattr(self, attr).get()

    def _build_config(self) -> SearchConfig:
        ezsf_text = self._current_ezsf_text()
        gui_filters: dict = {
            "version": self.version_var.get(),
            "stronghold_under_spawn": self.stronghold_under.get() or self._var_get("sh_under_spawn"),
            "stronghold_full": self.stronghold_full.get() or self._var_get("sh_full"),
            "ezsf_enabled": bool(ezsf_text),
            "ezsf_text": ezsf_text,
        }
        for key, var in self.dist_vars.items():
            gui_filters[f"{key}_enabled"] = self.dist_enabled[key].get()
            if self.dist_enabled[key].get():
                try:
                    gui_filters[key] = int(var.get() or "0")
                except ValueError:
                    gui_filters[key] = 0

        if self._var_get("spawn_require_dist"):
            gui_filters["spawn_dist_enabled"] = True
            try:
                gui_filters["spawn_max_dist"] = int(self._var_get("spawn_max_dist", "") or "0")
            except ValueError:
                gui_filters["spawn_max_dist"] = 0
            biomes = str(self._var_get("spawn_biomes", "")).strip()
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
        self._results = []
        self._clear_result_details()
        self._paused = False

        config = self._build_config()
        self._finder = SeedFinder(config)

        self.start_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal", text="Pause")
        self.stop_btn.configure(state="normal")
        self._progress_start()
        self.status_var.set("Searching...")

        def run():
            try:
                self._finder.search(
                    on_result=lambda r: self.after(0, lambda: self._add_result(r)),
                    on_progress=lambda n, rate: self.after(
                        0,
                        lambda n=n, rate=rate: self.status_var.set(
                            f"Searched {n:,} seeds @ {rate:,.0f}/s"
                        ),
                    ),
                )
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Search Error", str(exc)))
            finally:
                self.after(0, self._search_finished)

        self._search_thread = threading.Thread(target=run, daemon=True)
        self._search_thread.start()

    def _toggle_pause(self) -> None:
        if not self._finder:
            return
        self._paused = not self._paused
        if self._paused:
            self._finder.pause()
            self.pause_btn.configure(text="Resume")
            self.progress.pause()
            self.status_var.set("Paused")
        else:
            self._finder.resume()
            self.pause_btn.configure(text="Pause")
            self.progress.resume()
            self.status_var.set("Searching...")

    def _stop_search(self) -> None:
        if self._finder:
            self._finder.stop()

    def _search_finished(self) -> None:
        self._progress_stop()
        self.start_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled", text="Pause")
        self.stop_btn.configure(state="disabled")
        self._paused = False
        count = len(self._results)
        rate = self._finder.rate if self._finder else 0
        self.status_var.set(f"Done — found {count} seed(s) @ {rate:,.0f} seeds/s")

    def _format_details(self, details: dict[str, Any]) -> str:
        lines: list[str] = []
        for key in sorted(details):
            lines.append(f"{key}: {details[key]}")
        return "\n".join(lines)

    def _clear_result_details(self) -> None:
        self._text_clear(self.result_detail_text, disabled=True)

    def _on_result_select(self, _event: object = None) -> None:
        sel = self.results_tree.selection()
        if not sel:
            return
        idx = self.results_tree.index(sel[0])
        if idx < 0 or idx >= len(self._results):
            return
        result = self._results[idx]
        text = self._format_details(result.details)
        self.result_detail_text.configure(state="normal")
        self.result_detail_text.delete("1.0", "end")
        self.result_detail_text.insert("1.0", f"Seed: {result.seed}\n\n{text}")
        self.result_detail_text.configure(state="disabled")

    def _add_result(self, result: SeedResult) -> None:
        self._results.append(result)
        spawn = result.details.get("spawn", ("?", "?"))
        spawn_str = f"{spawn[0]}, {spawn[1]}"
        detail_parts = []
        for k, v in result.details.items():
            if k == "spawn":
                continue
            detail_parts.append(f"{k}={v}")
        summary = "; ".join(detail_parts[:4])
        if len(detail_parts) > 4:
            summary += " …"
        self.results_tree.insert("", tk.END, values=(result.seed, spawn_str, summary))
        if len(self._results) == 1:
            self.results_tree.selection_set(self.results_tree.get_children()[0])
            self._on_result_select()

    def _export_results(self, fmt: str) -> None:
        if not self._results:
            messagebox.showinfo("Export", "No results to export.")
            return
        ext = "json" if fmt == "json" else "txt"
        path = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            filetypes=[(ext.upper(), f"*.{ext}")],
        )
        if not path:
            return
        write_results(Path(path), self._results, fmt)
        self.status_var.set(f"Exported {len(self._results)} seed(s) to {os.path.basename(path)}")

    def _verify_seed(self) -> None:
        raw = self.verify_seed_var.get().strip()
        if not raw:
            messagebox.showinfo("Verify seed", "Enter a seed to check.")
            return
        try:
            seed = int(raw)
        except ValueError:
            messagebox.showerror("Verify seed", "Invalid seed — use an integer.")
            return
        config = self._build_config()
        checker = SeedChecker(
            doc=config.criteria_ast,
            gui_filters=config.gui_filters,
        )
        try:
            ok, details, rules = checker.check_detailed(seed)
        except Exception as exc:
            messagebox.showerror("Verify seed", str(exc))
            return
        lines = [f"Seed {seed}: {'PASS' if ok else 'FAIL'}", ""]
        for rule in rules:
            mark = "✓" if rule["ok"] else "✗"
            lines.append(f"  {mark} {rule['name']}")
        lines.append("")
        lines.append("Details:")
        lines.append(self._format_details(details))
        self.result_detail_text.configure(state="normal")
        self.result_detail_text.delete("1.0", "end")
        self.result_detail_text.insert("1.0", "\n".join(lines))
        self.result_detail_text.configure(state="disabled")
        self.status_var.set(f"Verify {seed}: {'pass' if ok else 'fail'}")

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
