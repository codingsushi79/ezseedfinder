"""Dark UI theme — default look for EZ Seed Finder."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from typing import Any
from tkinter import ttk


@dataclass(frozen=True)
class DarkTheme:
    bg: str = "#12131a"
    surface: str = "#1a1b24"
    surface_raised: str = "#22232e"
    border: str = "#2e3140"
    border_subtle: str = "#252833"
    fg: str = "#e8eaef"
    fg_muted: str = "#9498ab"
    accent: str = "#5b8def"
    accent_hover: str = "#4a7de0"
    accent_fg: str = "#ffffff"
    input_bg: str = "#282a36"
    select_bg: str = "#3d5080"
    code_bg: str = "#16171f"
    success: str = "#5ecf8a"
    danger: str = "#e06060"
    tab_selected: str = "#282a36"
    row_alt: str = "#1e1f28"


THEME = DarkTheme()

_UI_FONT = ("Segoe UI", 10)
_HEADER_FONT = ("Segoe UI", 11, "bold")
_STATUS_FONT = ("Consolas", 10)
_CODE_FONT = ("JetBrains Mono", 10)
_CODE_FONT_FALLBACK = ("Consolas", 10)


def _code_font() -> tuple[str, int]:
    families = set(tkfont.families())
    if "JetBrains Mono" in families:
        return _CODE_FONT
    if "Fira Code" in families:
        return ("Fira Code", 10)
    return _CODE_FONT_FALLBACK


def _flat_bevel(style: ttk.Style, name: str, bg: str, *, border: str | None = None) -> None:
    """Remove clam's white 3D highlight lines."""
    border = border or bg
    style.configure(
        name,
        lightcolor=bg,
        darkcolor=bg,
        bordercolor=border,
    )


def _strip_clam_borders(style: ttk.Style) -> None:
    """Drop clam border elements that draw bright 1px outlines on Linux."""
    style.layout(
        "TLabelframe",
        [
            (
                "Labelframe.padding",
                {
                    "sticky": "nswe",
                    "children": [
                        ("Labelframe.label", {"side": "top", "sticky": ""}),
                        ("Labelframe.client", {"sticky": "nswe"}),
                    ],
                },
            )
        ],
    )
    style.layout(
        "TEntry",
        [
            (
                "Entry.padding",
                {
                    "sticky": "nswe",
                    "children": [("Entry.textarea", {"sticky": "nswe"})],
                },
            )
        ],
    )
    style.layout(
        "TButton",
        [
            (
                "Button.padding",
                {
                    "sticky": "nswe",
                    "children": [("Button.label", {"sticky": "nswe"})],
                },
            )
        ],
    )
    style.layout(
        "TCombobox",
        [
            ("Combobox.downarrow", {"side": "right", "sticky": "ns"}),
            (
                "Combobox.padding",
                {
                    "sticky": "nswe",
                    "children": [("Combobox.textarea", {"sticky": "nswe"})],
                },
            ),
        ],
    )


def apply_dark_theme(root: tk.Misc) -> DarkTheme:
    """Apply dark ttk + tk styling. Call after widgets are built to style Text widgets too."""
    t = THEME
    root.configure(bg=t.bg)
    root.option_add("*highlightThickness", 0)
    root.option_add("*borderWidth", 0)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    _strip_clam_borders(style)

    # Base — flat, no default bevel
    style.configure(
        ".",
        background=t.bg,
        foreground=t.fg,
        bordercolor=t.border_subtle,
        lightcolor=t.bg,
        darkcolor=t.bg,
        relief=tk.FLAT,
    )
    style.configure("TFrame", background=t.bg, borderwidth=0)
    _flat_bevel(style, "TFrame", t.bg)

    style.configure("TLabel", background=t.bg, foreground=t.fg, font=_UI_FONT)
    _flat_bevel(style, "TLabel", t.bg)

    style.configure("Header.TLabel", background=t.bg, foreground=t.fg, font=_HEADER_FONT)
    style.configure("Muted.TLabel", background=t.bg, foreground=t.fg_muted, font=("Segoe UI", 9))

    style.configure("StatusBar.TFrame", background=t.surface)
    _flat_bevel(style, "StatusBar.TFrame", t.surface)
    style.configure(
        "Status.TLabel",
        background=t.surface,
        foreground=t.fg_muted,
        font=_STATUS_FONT,
        padding=(4, 2),
    )

    # Sections — flat card on surface, no groove border
    style.configure(
        "TLabelframe",
        background=t.surface,
        foreground=t.fg_muted,
        borderwidth=0,
        relief=tk.FLAT,
        bordercolor=t.border_subtle,
        lightcolor=t.surface,
        darkcolor=t.surface,
    )
    _flat_bevel(style, "TLabelframe", t.surface, border=t.border_subtle)
    style.configure(
        "TLabelframe.Label",
        background=t.surface,
        foreground=t.fg,
        font=_HEADER_FONT,
    )
    # Labels/checkboxes inside labelframes should match surface bg
    style.configure("Surface.TLabel", background=t.surface, foreground=t.fg, font=_UI_FONT)
    style.configure("SurfaceMuted.TLabel", background=t.surface, foreground=t.fg_muted, font=("Segoe UI", 9))
    style.configure("Surface.TCheckbutton", background=t.surface, foreground=t.fg, font=_UI_FONT)
    _flat_bevel(style, "Surface.TCheckbutton", t.surface)
    style.configure("Surface.TFrame", background=t.surface)
    _flat_bevel(style, "Surface.TFrame", t.surface)
    style.map(
        "Surface.TCheckbutton",
        background=[("active", t.surface), ("disabled", t.surface)],
        foreground=[("disabled", t.fg_muted)],
    )

    # Inputs
    style.configure(
        "TEntry",
        fieldbackground=t.input_bg,
        foreground=t.fg,
        insertcolor=t.fg,
        borderwidth=0,
        relief=tk.FLAT,
        padding=4,
    )
    _flat_bevel(style, "TEntry", t.input_bg, border=t.border_subtle)

    style.configure(
        "TCombobox",
        fieldbackground=t.input_bg,
        foreground=t.fg,
        arrowcolor=t.fg_muted,
        borderwidth=0,
        relief=tk.FLAT,
        padding=4,
    )
    _flat_bevel(style, "TCombobox", t.input_bg, border=t.border_subtle)
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", t.input_bg)],
        selectbackground=[("readonly", t.select_bg)],
        selectforeground=[("readonly", t.fg)],
    )

    # Check / radio
    style.configure("TCheckbutton", background=t.bg, foreground=t.fg, font=_UI_FONT, focuscolor=t.bg)
    _flat_bevel(style, "TCheckbutton", t.bg)
    style.configure("TRadiobutton", background=t.bg, foreground=t.fg, font=_UI_FONT, focuscolor=t.bg)
    _flat_bevel(style, "TRadiobutton", t.bg)
    style.map(
        "TCheckbutton",
        background=[("active", t.bg), ("disabled", t.bg)],
        foreground=[("disabled", t.fg_muted)],
        focuscolor=[("focus", t.bg)],
    )

    # Buttons — flat, no white bevel
    style.configure(
        "TButton",
        background=t.surface_raised,
        foreground=t.fg,
        borderwidth=0,
        relief=tk.FLAT,
        padding=(10, 6),
        font=_UI_FONT,
        focuscolor=t.bg,
    )
    _flat_bevel(style, "TButton", t.surface_raised, border=t.border)
    style.map(
        "TButton",
        background=[("active", t.border), ("pressed", t.input_bg)],
        foreground=[("disabled", t.fg_muted)],
        focuscolor=[("focus", t.bg)],
    )

    style.configure(
        "Primary.TButton",
        background=t.accent,
        foreground=t.accent_fg,
        borderwidth=0,
        relief=tk.FLAT,
        padding=(12, 7),
        font=("Segoe UI", 10, "bold"),
        focuscolor=t.bg,
    )
    _flat_bevel(style, "Primary.TButton", t.accent, border=t.accent)
    style.map(
        "Primary.TButton",
        background=[("active", t.accent_hover), ("pressed", t.accent_hover)],
        foreground=[("disabled", t.fg_muted)],
    )

    style.configure(
        "Danger.TButton",
        background="#3a2528",
        foreground="#f0a0a0",
        borderwidth=1,
        relief=tk.FLAT,
        padding=(10, 6),
        focuscolor=t.bg,
    )
    _flat_bevel(style, "Danger.TButton", "#3a2528", border="#5a3035")
    style.map("Danger.TButton", background=[("active", "#4a3035")])

    # Notebook — no outer border
    style.configure("TNotebook", background=t.bg, borderwidth=0, tabmargins=[2, 6, 2, 0])
    _flat_bevel(style, "TNotebook", t.bg)
    style.configure(
        "TNotebook.Tab",
        background=t.surface,
        foreground=t.fg_muted,
        padding=[14, 7],
        font=_UI_FONT,
        borderwidth=0,
    )
    _flat_bevel(style, "TNotebook.Tab", t.surface)
    style.map(
        "TNotebook.Tab",
        background=[("selected", t.tab_selected), ("active", t.surface_raised)],
        foreground=[("selected", t.fg), ("active", t.fg)],
        expand=[("selected", [1, 1, 1, 0])],
    )

    # Treeview — flat, no grid lines
    style.configure(
        "Treeview",
        background=t.input_bg,
        foreground=t.fg,
        fieldbackground=t.input_bg,
        borderwidth=0,
        relief=tk.FLAT,
        rowheight=26,
        font=_UI_FONT,
    )
    _flat_bevel(style, "Treeview", t.input_bg)
    style.configure(
        "Treeview.Heading",
        background=t.surface_raised,
        foreground=t.fg,
        relief=tk.FLAT,
        borderwidth=0,
        font=("Segoe UI", 10, "bold"),
        padding=6,
    )
    _flat_bevel(style, "Treeview.Heading", t.surface_raised)
    style.map(
        "Treeview",
        background=[("selected", t.select_bg)],
        foreground=[("selected", t.fg)],
    )

    # Scrollbars
    style.configure(
        "Vertical.TScrollbar",
        background=t.surface_raised,
        troughcolor=t.surface,
        borderwidth=0,
        arrowcolor=t.fg_muted,
        relief=tk.FLAT,
    )
    _flat_bevel(style, "Vertical.TScrollbar", t.surface_raised)
    style.configure(
        "Horizontal.TScrollbar",
        background=t.surface_raised,
        troughcolor=t.surface,
        borderwidth=0,
        arrowcolor=t.fg_muted,
        relief=tk.FLAT,
    )
    _flat_bevel(style, "Horizontal.TScrollbar", t.surface_raised)

    style.configure(
        "TProgressbar",
        background=t.accent,
        troughcolor=t.surface,
        borderwidth=0,
        thickness=8,
    )
    _flat_bevel(style, "TProgressbar", t.surface)

    # Paned window — dark sash, no bright divider
    style.configure("TPanedwindow", background=t.bg, borderwidth=0)
    _flat_bevel(style, "TPanedwindow", t.bg)
    style.configure("Sash", sashthickness=5, background=t.border_subtle, sashrelief=tk.FLAT)
    _flat_bevel(style, "Sash", t.border_subtle)

    # tk default fonts
    try:
        for name in ("TkDefaultFont", "TkTextFont", "TkFixedFont"):
            tkfont.nametofont(name).configure(family="Segoe UI", size=10)
        tkfont.nametofont("TkFixedFont").configure(family=_code_font()[0], size=10)
    except tk.TclError:
        pass

    return t


def add_scrolled_text(parent: tk.Misc, *, theme: DarkTheme | None = None, **text_kw: Any) -> tk.Text:
    """Text area with dark ttk scrollbars (avoids tk's light native scrollbar borders)."""
    t = theme or THEME
    frame = tk.Frame(parent, bg=t.code_bg, highlightthickness=0, borderwidth=0)
    text = tk.Text(frame, **text_kw)
    style_text_widget(text, t)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
    text.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    if text_kw.get("wrap") is tk.NONE:
        hsb = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=text.xview)
        text.configure(xscrollcommand=hsb.set)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
    frame.pack(fill=tk.BOTH, expand=True)
    return text


def style_text_widget(text: tk.Text, theme: DarkTheme | None = None) -> None:
    t = theme or THEME
    text.configure(
        bg=t.code_bg,
        fg=t.fg,
        insertbackground=t.fg,
        selectbackground=t.select_bg,
        selectforeground=t.fg,
        relief=tk.FLAT,
        borderwidth=0,
        highlightthickness=0,
        padx=8,
        pady=8,
        font=_code_font(),
    )


def style_canvas(canvas: tk.Canvas, theme: DarkTheme | None = None) -> None:
    t = theme or THEME
    canvas.configure(
        bg=t.bg,
        highlightthickness=0,
        borderwidth=0,
    )
