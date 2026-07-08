"""Reusable CustomTkinter widgets for criteria panels."""

from __future__ import annotations

import tkinter as tk
from typing import Any

import customtkinter as ctk

from .theme import COLORS, FONT_SMALL, FONT_UI, combo, muted

REF_PRESETS = ("spawn", "origin", "0,0", "custom")
DIMENSIONS = ("overworld", "nether", "end")
BASTION_VARIANTS = ("treasure", "housing", "stables", "bridge")
PORTAL_TEMPLATES = ("", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10")
DEFAULT_LOOT_ITEMS = (
    "obsidian",
    "flint_and_steel",
    "fire_charge",
    "flint",
    "gold_ingot",
    "gold_nugget",
    "golden_apple",
    "enchanted_golden_apple",
    "heart_of_the_sea",
    "diamond",
    "emerald",
    "iron_ingot",
    "tnt",
)
LOOT_ITEMS = DEFAULT_LOOT_ITEMS
MOB_TYPES = (
    "witch", "slime", "magma_cube", "ghast", "blaze", "enderman", "piglin",
    "zombie", "skeleton", "creeper", "spider", "pillager", "villager",
    "husk", "stray", "phantom", "drowned", "guardian", "shulker", "strider",
)
TERRAIN_TYPES = ("flat", "mountainous", "oceanic")
COMPARE_OPS = ("<=", ">=", "==", "<", ">")


def apply_ui_fonts(root) -> None:
    from .theme import setup_theme

    setup_theme()


def scrollable_tab(parent: ctk.CTkFrame) -> ctk.CTkScrollableFrame:
    scroll = ctk.CTkScrollableFrame(
        parent,
        fg_color="transparent",
        scrollbar_button_color=COLORS["surface_raised"],
        scrollbar_button_hover_color=COLORS["border"],
        label_fg_color="transparent",
    )
    scroll.pack(fill="both", expand=True, padx=12, pady=10)
    return scroll


def toggle_block(parent: ctk.CTkBaseClass, title: str) -> tuple[ctk.CTkFrame, tk.BooleanVar]:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", pady=6)
    enabled = tk.BooleanVar(value=False)
    ctk.CTkCheckBox(
        frame,
        text=title,
        variable=enabled,
        font=FONT_UI,
        fg_color=COLORS["accent"],
        hover_color=COLORS["accent_hover"],
        border_color=COLORS["border"],
    ).pack(anchor="w")
    body = ctk.CTkFrame(frame, fg_color="transparent")
    body.pack(fill="x", padx=(22, 0))

    def _toggle(*_a: object) -> None:
        if enabled.get():
            body.pack(fill="x", padx=(22, 0), pady=(4, 0))
        else:
            body.pack_forget()

    enabled.trace_add("write", _toggle)
    _toggle()
    return body, enabled


def structure_checkbox(parent: ctk.CTkBaseClass, label: str) -> tk.BooleanVar:
    enabled = tk.BooleanVar(value=False)
    ctk.CTkCheckBox(
        parent,
        text=label,
        variable=enabled,
        font=FONT_UI,
        fg_color=COLORS["accent"],
        hover_color=COLORS["accent_hover"],
        border_color=COLORS["border"],
    ).pack(anchor="w", pady=2)
    return enabled


def labeled_entry(
    parent: ctk.CTkBaseClass,
    label: str,
    default: str = "",
    width: int = 120,
) -> tk.StringVar:
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=4)
    ctk.CTkLabel(row, text=label, font=FONT_UI, anchor="w", width=180).pack(side="left")
    var = tk.StringVar(value=default)
    ctk.CTkEntry(
        row,
        textvariable=var,
        width=width,
        height=32,
        corner_radius=8,
        fg_color=COLORS["input"],
        border_color=COLORS["border_subtle"],
        font=FONT_UI,
    ).pack(side="right")
    return var


def labeled_combo(
    parent: ctk.CTkBaseClass,
    label: str,
    values: tuple[str, ...],
    default: str = "",
    width: int = 160,
) -> tk.StringVar:
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=4)
    ctk.CTkLabel(row, text=label, font=FONT_UI, anchor="w", width=180).pack(side="left")
    var = tk.StringVar(value=default)
    widget = combo(
        row,
        values=list(values) if values else [""],
        variable=var,
        width=width,
        state="readonly",
    )
    widget.pack(side="right")
    widget._ezsf_values = values  # type: ignore[attr-defined]
    return var


def ref_row(parent: ctk.CTkBaseClass, default_ref: str = "spawn") -> dict[str, Any]:
    ref_var = labeled_combo(parent, "Reference point", REF_PRESETS, default_ref)
    custom_var = labeled_entry(parent, "Custom ref (x,z)", "")
    return {"ref": ref_var, "custom": custom_var}


def resolve_ref(data: dict[str, Any]) -> tuple[str, tuple[int, int] | None]:
    ref = data["ref"].get().strip()
    custom = data["custom"].get().strip()
    if ref == "custom" or custom:
        if custom:
            parts = [p.strip() for p in custom.split(",")]
            if len(parts) == 2:
                try:
                    return "origin", (int(parts[0]), int(parts[1]))
                except ValueError:
                    pass
    if ref == "0,0":
        return "origin", (0, 0)
    return ref or "spawn", None


def set_ref(data: dict[str, Any], ref: str, ref_pos: tuple[int, int] | None) -> None:
    if ref_pos is not None:
        data["ref"].set("custom")
        data["custom"].set(f"{ref_pos[0]},{ref_pos[1]}")
    elif ref in ("spawn", "origin"):
        data["ref"].set(ref)
        data["custom"].set("")
    elif ref == "0,0":
        data["ref"].set("0,0")
        data["custom"].set("")
    else:
        data["ref"].set("custom")
        data["custom"].set(ref)


def dist_row(parent: ctk.CTkBaseClass, default: str = "500") -> tk.StringVar:
    return labeled_entry(parent, "Max distance (blocks)", default)


def chest_item_row(
    parent: ctk.CTkBaseClass,
    item_values: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=4)
    item_var = tk.StringVar(value="obsidian")
    count_var = tk.StringVar(value="1")
    values = item_values or DEFAULT_LOOT_ITEMS
    widget = combo(
        row,
        values=list(values),
        variable=item_var,
        width=180,
        state="readonly",
    )
    widget.pack(side="left", padx=(0, 6))
    ctk.CTkLabel(row, text="min", font=FONT_SMALL).pack(side="left")
    ctk.CTkEntry(
        row,
        textvariable=count_var,
        width=56,
        height=32,
        corner_radius=8,
        fg_color=COLORS["input"],
        font=FONT_UI,
    ).pack(side="left", padx=6)
    return {"row": row, "item": item_var, "count": count_var, "combo": widget}
