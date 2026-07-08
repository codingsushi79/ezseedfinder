"""Reusable GUI widgets for .ezsf criteria panels."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

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

_UI_FONT = ("Segoe UI", 10)


def apply_ui_fonts(root: tk.Misc) -> None:
    """Legacy hook — fonts are configured by apply_dark_theme."""
    from .theme import apply_dark_theme

    apply_dark_theme(root)


def scrollable_tab(parent: ttk.Frame) -> ttk.Frame:
    from .theme import style_canvas

    canvas = tk.Canvas(parent, highlightthickness=0)
    scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
    inner = ttk.Frame(canvas)
    inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    win = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_canvas_configure(event: tk.Event) -> None:
        canvas.itemconfigure(win, width=event.width)

    canvas.bind("<Configure>", _on_canvas_configure)
    canvas.configure(yscrollcommand=scroll.set)
    style_canvas(canvas)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _wheel(event: tk.Event) -> str | None:
        if event.delta:
            canvas.yview_scroll(int(-event.delta / 120), "units")
        elif event.num == 4:
            canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            canvas.yview_scroll(1, "units")
        return "break"

    for w in (canvas, inner):
        w.bind("<MouseWheel>", _wheel)
        w.bind("<Button-4>", _wheel)
        w.bind("<Button-5>", _wheel)
    return inner


def section(parent: ttk.Frame, title: str) -> tuple[ttk.LabelFrame, tk.BooleanVar]:
    enabled = tk.BooleanVar(value=False)
    frame = ttk.LabelFrame(parent, text=title, padding=8)
    frame.pack(fill=tk.X, pady=4)
    head = ttk.Frame(frame)
    head.pack(fill=tk.X, pady=(0, 6))
    ttk.Checkbutton(head, text="Enable", variable=enabled).pack(side=tk.LEFT)
    body = ttk.Frame(frame)
    body.pack(fill=tk.X)

    def _toggle(*_a: object) -> None:
        state = "normal" if enabled.get() else "disabled"
        for child in _walk(body):
            try:
                child.configure(state=state)
            except tk.TclError:
                pass

    enabled.trace_add("write", _toggle)
    _toggle()
    return body, enabled


def toggle_block(parent: ttk.Frame, title: str) -> tuple[ttk.Frame, tk.BooleanVar]:
    """Checkbox header that shows/hides a detail frame (no 'Enable' label)."""
    frame = ttk.Frame(parent)
    frame.pack(fill=tk.X, pady=4)
    enabled = tk.BooleanVar(value=False)
    head = ttk.Frame(frame)
    head.pack(fill=tk.X)
    ttk.Checkbutton(head, text=title, variable=enabled).pack(side=tk.LEFT)
    body = ttk.Frame(frame)
    body.pack(fill=tk.X, padx=(18, 0))

    def _toggle(*_a: object) -> None:
        if enabled.get():
            body.pack(fill=tk.X, padx=(18, 0), pady=(2, 0))
        else:
            body.pack_forget()

    enabled.trace_add("write", _toggle)
    _toggle()
    return body, enabled


def structure_checkbox(parent: ttk.Frame, label: str) -> tk.BooleanVar:
    """Structure picker checkbox (config lives on a separate tab)."""
    enabled = tk.BooleanVar(value=False)
    ttk.Checkbutton(parent, text=label, variable=enabled).pack(anchor=tk.W, pady=1)
    return enabled


def structure_toggle_row(
    parent: ttk.Frame,
    label: str,
    name: str,
    dim: str,
    default_dist: str = "500",
) -> dict[str, Any]:
    frame = ttk.Frame(parent)
    frame.pack(fill=tk.X, pady=2)
    enabled = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text=label, variable=enabled).pack(anchor=tk.W)
    details = ttk.Frame(frame)
    ref = ref_row(details, "spawn")
    dist = dist_row(details, default_dist)
    viable = tk.BooleanVar(value=True)
    ttk.Checkbutton(details, text="Must be viable", variable=viable).pack(anchor=tk.W)

    def _toggle(*_a: object) -> None:
        if enabled.get():
            details.pack(fill=tk.X, padx=(18, 0), pady=(2, 0))
        else:
            details.pack_forget()

    enabled.trace_add("write", _toggle)
    _toggle()
    return {
        "enabled": enabled,
        "name": name,
        "dimension": dim,
        "ref": ref,
        "max_dist": dist,
        "viable": viable,
    }


def _walk(widget: tk.Misc) -> list[tk.Misc]:
    out: list[tk.Misc] = []
    for child in widget.winfo_children():
        out.append(child)
        out.extend(_walk(child))
    return out


def labeled_entry(
    parent: ttk.Frame,
    label: str,
    default: str = "",
    width: int = 12,
) -> tk.StringVar:
    row = ttk.Frame(parent)
    row.pack(fill=tk.X, pady=3)
    ttk.Label(row, text=label, width=22).pack(side=tk.LEFT)
    var = tk.StringVar(value=default)
    ttk.Entry(row, textvariable=var, width=width).pack(side=tk.RIGHT)
    return var


def labeled_combo(
    parent: ttk.Frame,
    label: str,
    values: tuple[str, ...],
    default: str = "",
    width: int = 14,
) -> tk.StringVar:
    row = ttk.Frame(parent)
    row.pack(fill=tk.X, pady=3)
    ttk.Label(row, text=label, width=22).pack(side=tk.LEFT)
    var = tk.StringVar(value=default)
    ttk.Combobox(row, textvariable=var, values=values, width=width, state="readonly").pack(
        side=tk.RIGHT
    )
    return var


def ref_row(parent: ttk.Frame, default_ref: str = "spawn") -> dict[str, Any]:
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


def dist_row(parent: ttk.Frame, default: str = "500") -> tk.StringVar:
    return labeled_entry(parent, "Max distance (blocks)", default)


def chest_item_row(
    parent: ttk.Frame,
    item_values: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    row = ttk.Frame(parent)
    row.pack(fill=tk.X, pady=3)
    item_var = tk.StringVar(value="obsidian")
    count_var = tk.StringVar(value="1")
    values = item_values or DEFAULT_LOOT_ITEMS
    combo = ttk.Combobox(
        row,
        textvariable=item_var,
        values=values,
        width=18,
        state="readonly",
    )
    combo.pack(side=tk.LEFT, padx=(0, 4))
    ttk.Label(row, text="min").pack(side=tk.LEFT)
    ttk.Entry(row, textvariable=count_var, width=5).pack(side=tk.LEFT, padx=4)
    return {"row": row, "item": item_var, "count": count_var, "combo": combo}
