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

_UI_FAMILY: str | None = None
_CODE_FAMILY: str | None = None

_UI_FAMILY_CANDIDATES = (
    "Segoe UI",
    "Ubuntu",
    "Noto Sans",
    "Inter",
    "DejaVu Sans",
    "Liberation Sans",
    "Cantarell",
    "Helvetica Neue",
    "Arial",
)
_CODE_FAMILY_CANDIDATES = (
    "JetBrains Mono",
    "Fira Code",
    "Cascadia Mono",
    "Consolas",
    "DejaVu Sans Mono",
    "Liberation Mono",
    "Ubuntu Mono",
)


def _pick_family(candidates: tuple[str, ...], root: tk.Misc) -> str:
    available = {name.lower(): name for name in tkfont.families(root)}
    for candidate in candidates:
        if candidate.lower() in available:
            return available[candidate.lower()]
    return tkfont.nametofont("TkDefaultFont").actual("family", displayof=root)


def _resolve_fonts(root: tk.Misc) -> None:
    global _UI_FAMILY, _CODE_FAMILY
    _UI_FAMILY = _pick_family(_UI_FAMILY_CANDIDATES, root)
    _CODE_FAMILY = _pick_family(_CODE_FAMILY_CANDIDATES, root)


def ui_font(size: int = 10, *, bold: bool = False) -> tuple[str, int] | tuple[str, int, str]:
    family = _UI_FAMILY or "sans-serif"
    if bold:
        return (family, size, "bold")
    return (family, size)


def code_font(size: int = 10) -> tuple[str, int]:
    return (_CODE_FAMILY or "TkFixedFont", size)


def _flat_bevel(style: ttk.Style, name: str, bg: str, *, border: str | None = None) -> None:
    """Remove clam's white 3D highlight lines."""
    border = border or bg
    style.configure(
        name,
        lightcolor=bg,
        darkcolor=bg,
        bordercolor=border,
    )


def _strip_labelframe_border(style: ttk.Style) -> None:
    """Labelframe border element draws bright outlines; use padding-only layout."""
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


def _apply_tk_options(root: tk.Misc, t: DarkTheme) -> None:
    root.option_add("*highlightThickness", 0)
    root.option_add("*borderWidth", 0)
    root.option_add("*Font", ui_font())
    root.option_add("*Background", t.bg)
    root.option_add("*Foreground", t.fg)
    root.option_add("*selectBackground", t.select_bg)
    root.option_add("*selectForeground", t.fg)
    root.option_add("*insertBackground", t.fg)
    root.option_add("*TCombobox*Listbox.background", t.input_bg)
    root.option_add("*TCombobox*Listbox.foreground", t.fg)
    root.option_add("*TCombobox*Listbox.selectBackground", t.select_bg)
    root.option_add("*TCombobox*Listbox.selectForeground", t.fg)
    root.option_add("*TCombobox*Listbox.highlightThickness", 0)
    root.option_add("*TCombobox*Listbox.borderWidth", 0)


def apply_dark_theme(root: tk.Misc) -> DarkTheme:
    """Apply dark ttk + tk styling."""
    t = THEME
    _resolve_fonts(root)
    root.configure(bg=t.bg)
    _apply_tk_options(root, t)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    _strip_labelframe_border(style)

    # Base — flat, no default bevel
    style.configure(
        ".",
        background=t.bg,
        foreground=t.fg,
        bordercolor=t.border_subtle,
        lightcolor=t.bg,
        darkcolor=t.bg,
        relief=tk.FLAT,
        font=ui_font(),
    )
    style.configure("TFrame", background=t.bg, borderwidth=0)
    _flat_bevel(style, "TFrame", t.bg)

    style.configure("TLabel", background=t.bg, foreground=t.fg, font=ui_font())
    _flat_bevel(style, "TLabel", t.bg)

    style.configure("Header.TLabel", background=t.bg, foreground=t.fg, font=ui_font(11, bold=True))
    style.configure("Muted.TLabel", background=t.bg, foreground=t.fg_muted, font=ui_font(9))

    style.configure("StatusBar.TFrame", background=t.surface)
    _flat_bevel(style, "StatusBar.TFrame", t.surface)
    style.configure(
        "Status.TLabel",
        background=t.surface,
        foreground=t.fg_muted,
        font=code_font(),
        padding=(4, 2),
    )

    # Sections — flat card on surface
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
        font=ui_font(11, bold=True),
    )
    style.configure("Surface.TLabel", background=t.surface, foreground=t.fg, font=ui_font())
    style.configure("SurfaceMuted.TLabel", background=t.surface, foreground=t.fg_muted, font=ui_font(9))
    style.configure("Surface.TCheckbutton", background=t.surface, foreground=t.fg, font=ui_font())
    _flat_bevel(style, "Surface.TCheckbutton", t.surface)
    style.configure("Surface.TFrame", background=t.surface)
    _flat_bevel(style, "Surface.TFrame", t.surface)
    style.map(
        "Surface.TCheckbutton",
        background=[("active", t.surface), ("disabled", t.surface)],
        foreground=[("disabled", t.fg_muted)],
    )

    # Inputs — keep clam field/border elements so fieldbackground paints correctly
    style.configure(
        "TEntry",
        fieldbackground=t.input_bg,
        foreground=t.fg,
        insertcolor=t.fg,
        background=t.input_bg,
        borderwidth=1,
        relief=tk.FLAT,
        padding=4,
    )
    _flat_bevel(style, "TEntry", t.input_bg, border=t.border_subtle)

    style.configure(
        "TCombobox",
        fieldbackground=t.input_bg,
        foreground=t.fg,
        background=t.input_bg,
        arrowcolor=t.fg_muted,
        borderwidth=1,
        relief=tk.FLAT,
        padding=4,
    )
    _flat_bevel(style, "TCombobox", t.input_bg, border=t.border_subtle)
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", t.input_bg), ("disabled", t.surface)],
        selectbackground=[("readonly", t.select_bg)],
        selectforeground=[("readonly", t.fg)],
        foreground=[("disabled", t.fg_muted)],
    )

    # Check / radio
    style.configure("TCheckbutton", background=t.bg, foreground=t.fg, font=ui_font(), focuscolor=t.bg)
    _flat_bevel(style, "TCheckbutton", t.bg)
    style.configure("TRadiobutton", background=t.bg, foreground=t.fg, font=ui_font(), focuscolor=t.bg)
    _flat_bevel(style, "TRadiobutton", t.bg)
    style.map(
        "TCheckbutton",
        background=[("active", t.bg), ("disabled", t.bg)],
        foreground=[("disabled", t.fg_muted)],
        focuscolor=[("focus", t.bg)],
    )

    # Buttons
    style.configure(
        "TButton",
        background=t.surface_raised,
        foreground=t.fg,
        borderwidth=1,
        relief=tk.FLAT,
        padding=(10, 6),
        font=ui_font(),
        focuscolor=t.bg,
    )
    _flat_bevel(style, "TButton", t.surface_raised, border=t.border)
    style.map(
        "TButton",
        background=[("active", t.border), ("pressed", t.input_bg), ("disabled", t.surface)],
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
        font=ui_font(10, bold=True),
        focuscolor=t.bg,
    )
    _flat_bevel(style, "Primary.TButton", t.accent, border=t.accent)
    style.map(
        "Primary.TButton",
        background=[("active", t.accent_hover), ("pressed", t.accent_hover), ("disabled", t.surface)],
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
    style.map("Danger.TButton", background=[("active", "#4a3035"), ("disabled", t.surface)])

    # Notebook
    style.configure("TNotebook", background=t.bg, borderwidth=0, tabmargins=[2, 6, 2, 0])
    _flat_bevel(style, "TNotebook", t.bg)
    style.configure(
        "TNotebook.Tab",
        background=t.surface,
        foreground=t.fg_muted,
        padding=[14, 7],
        font=ui_font(),
        borderwidth=0,
    )
    _flat_bevel(style, "TNotebook.Tab", t.surface)
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
        borderwidth=0,
        relief=tk.FLAT,
        rowheight=26,
        font=ui_font(),
    )
    _flat_bevel(style, "Treeview", t.input_bg)
    style.configure(
        "Treeview.Heading",
        background=t.surface_raised,
        foreground=t.fg,
        relief=tk.FLAT,
        borderwidth=0,
        font=ui_font(10, bold=True),
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
        lightcolor=t.surface,
        darkcolor=t.surface,
        thickness=8,
    )
    _flat_bevel(style, "TProgressbar", t.surface)

    # Paned window
    style.configure("TPanedwindow", background=t.bg, borderwidth=0)
    _flat_bevel(style, "TPanedwindow", t.bg)
    style.configure("Sash", sashthickness=5, background=t.border_subtle, sashrelief=tk.FLAT)
    _flat_bevel(style, "Sash", t.border_subtle)

    # tk named fonts — use resolved families, not missing Windows-only names
    try:
        for name in ("TkDefaultFont", "TkTextFont"):
            tkfont.nametofont(name).configure(family=_UI_FAMILY, size=10)
        tkfont.nametofont("TkFixedFont").configure(family=_CODE_FAMILY, size=10)
        tkfont.nametofont("TkMenuFont").configure(family=_UI_FAMILY, size=10)
    except tk.TclError:
        pass

    return t


def add_scrolled_text(parent: tk.Misc, *, theme: DarkTheme | None = None, **text_kw: Any) -> tk.Text:
    """Text area with dark ttk scrollbars."""
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
        font=code_font(),
    )


def style_canvas(canvas: tk.Canvas, theme: DarkTheme | None = None) -> None:
    t = theme or THEME
    canvas.configure(
        bg=t.bg,
        highlightthickness=0,
        borderwidth=0,
    )
