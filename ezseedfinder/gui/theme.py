"""Dark UI theme — default look for EZ Seed Finder."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from tkinter import ttk


@dataclass(frozen=True)
class DarkTheme:
    bg: str = "#12131a"
    surface: str = "#1a1b24"
    surface_raised: str = "#22232e"
    border: str = "#343647"
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


def apply_dark_theme(root: tk.Misc) -> DarkTheme:
    """Apply dark ttk + tk styling. Call after widgets are built to style Text widgets too."""
    t = THEME
    root.configure(bg=t.bg)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # Base widgets
    style.configure(".", background=t.bg, foreground=t.fg, bordercolor=t.border)
    style.configure("TFrame", background=t.bg)
    style.configure("TLabel", background=t.bg, foreground=t.fg, font=_UI_FONT)
    style.configure(
        "Header.TLabel",
        background=t.bg,
        foreground=t.fg,
        font=_HEADER_FONT,
    )
    style.configure(
        "Muted.TLabel",
        background=t.bg,
        foreground=t.fg_muted,
        font=("Segoe UI", 9),
    )
    style.configure(
        "StatusBar.TFrame",
        background=t.surface,
    )
    style.configure(
        "Status.TLabel",
        background=t.surface,
        foreground=t.fg_muted,
        font=_STATUS_FONT,
        padding=(4, 2),
    )
    style.configure(
        "TLabelframe",
        background=t.bg,
        foreground=t.fg_muted,
        bordercolor=t.border,
        relief=tk.GROOVE,
    )
    style.configure(
        "TLabelframe.Label",
        background=t.bg,
        foreground=t.fg,
        font=_HEADER_FONT,
    )

    # Inputs
    style.configure(
        "TEntry",
        fieldbackground=t.input_bg,
        foreground=t.fg,
        insertcolor=t.fg,
        bordercolor=t.border,
        lightcolor=t.border,
        darkcolor=t.border,
        padding=4,
    )
    style.configure(
        "TCombobox",
        fieldbackground=t.input_bg,
        foreground=t.fg,
        arrowcolor=t.fg_muted,
        bordercolor=t.border,
        lightcolor=t.border,
        darkcolor=t.border,
        padding=4,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", t.input_bg)],
        selectbackground=[("readonly", t.select_bg)],
        selectforeground=[("readonly", t.fg)],
    )

    # Check / radio
    style.configure(
        "TCheckbutton",
        background=t.bg,
        foreground=t.fg,
        font=_UI_FONT,
    )
    style.configure(
        "TRadiobutton",
        background=t.bg,
        foreground=t.fg,
        font=_UI_FONT,
    )
    style.map(
        "TCheckbutton",
        background=[("active", t.bg), ("disabled", t.bg)],
        foreground=[("disabled", t.fg_muted)],
    )

    # Buttons
    style.configure(
        "TButton",
        background=t.surface_raised,
        foreground=t.fg,
        bordercolor=t.border,
        lightcolor=t.border,
        darkcolor=t.border,
        padding=(10, 6),
        font=_UI_FONT,
    )
    style.map(
        "TButton",
        background=[("active", t.border), ("pressed", t.input_bg)],
        foreground=[("disabled", t.fg_muted)],
    )
    style.configure(
        "Primary.TButton",
        background=t.accent,
        foreground=t.accent_fg,
        bordercolor=t.accent,
        lightcolor=t.accent,
        darkcolor=t.accent,
        padding=(12, 7),
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "Primary.TButton",
        background=[("active", t.accent_hover), ("pressed", t.accent_hover)],
        foreground=[("disabled", t.fg_muted)],
    )
    style.configure(
        "Danger.TButton",
        background="#3a2528",
        foreground="#f0a0a0",
        bordercolor="#5a3035",
        padding=(10, 6),
    )
    style.map("Danger.TButton", background=[("active", "#4a3035")])

    # Notebook
    style.configure("TNotebook", background=t.bg, borderwidth=0, tabmargins=[2, 6, 2, 0])
    style.configure(
        "TNotebook.Tab",
        background=t.surface,
        foreground=t.fg_muted,
        padding=[14, 7],
        font=_UI_FONT,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", t.tab_selected), ("active", t.surface_raised)],
        foreground=[("selected", t.fg), ("active", t.fg)],
        expand=[("selected", [1, 1, 1, 0])],
    )

    # Treeview
    style.configure(
        "Treeview",
        background=t.input_bg,
        foreground=t.fg,
        fieldbackground=t.input_bg,
        bordercolor=t.border,
        lightcolor=t.border,
        darkcolor=t.border,
        rowheight=26,
        font=_UI_FONT,
    )
    style.configure(
        "Treeview.Heading",
        background=t.surface_raised,
        foreground=t.fg,
        bordercolor=t.border,
        relief=tk.FLAT,
        font=("Segoe UI", 10, "bold"),
        padding=6,
    )
    style.map(
        "Treeview",
        background=[("selected", t.select_bg)],
        foreground=[("selected", t.fg)],
    )

    # Scrollbars & progress
    style.configure(
        "Vertical.TScrollbar",
        background=t.surface_raised,
        troughcolor=t.surface,
        bordercolor=t.border,
        arrowcolor=t.fg_muted,
    )
    style.configure(
        "Horizontal.TScrollbar",
        background=t.surface_raised,
        troughcolor=t.surface,
        bordercolor=t.border,
        arrowcolor=t.fg_muted,
    )
    style.configure(
        "TProgressbar",
        background=t.accent,
        troughcolor=t.surface,
        bordercolor=t.border,
        lightcolor=t.accent,
        darkcolor=t.accent,
        thickness=8,
    )

    # Paned window sash
    style.configure("TPanedwindow", background=t.bg)
    try:
        root.tk.call("ttk::style", "configure", "Sash", "-sashthickness", 6)
    except tk.TclError:
        pass

    # tk default fonts
    try:
        for name in ("TkDefaultFont", "TkTextFont", "TkFixedFont"):
            tkfont.nametofont(name).configure(family="Segoe UI", size=10)
        tkfont.nametofont("TkFixedFont").configure(family=_code_font()[0], size=10)
    except tk.TclError:
        pass

    return t


def style_text_widget(text: tk.Text, t: DarkTheme | None = None) -> None:
    theme = t or THEME
    text.configure(
        bg=theme.code_bg,
        fg=theme.fg,
        insertbackground=theme.fg,
        selectbackground=theme.select_bg,
        selectforeground=theme.fg,
        relief=tk.FLAT,
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=theme.border,
        highlightcolor=theme.accent,
        padx=8,
        pady=8,
        font=_code_font(),
    )


def style_canvas(canvas: tk.Canvas, t: DarkTheme | None = None) -> None:
    theme = t or THEME
    canvas.configure(
        bg=theme.bg,
        highlightthickness=0,
        borderwidth=0,
    )
