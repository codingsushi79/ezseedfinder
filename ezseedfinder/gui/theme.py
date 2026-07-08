"""CustomTkinter theme for EZ Seed Finder."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

# Shared palette
COLORS = {
    "bg": "#13141c",
    "surface": "#1c1d27",
    "surface_raised": "#252632",
    "tab_body": "#2e3040",
    "tab_active": "#353848",
    "border": "#3a3d4f",
    "border_subtle": "#2a2c38",
    "fg": "#eceef4",
    "fg_muted": "#9aa0b5",
    "accent": "#6b93f0",
    "accent_hover": "#5a82de",
    "input": "#2a2c3a",
    "code": "#181922",
    "select": "#455a8f",
    "danger": "#e87878",
    "danger_bg": "#3f2a2e",
}

FONT_UI = ("Ubuntu", 13)
FONT_HEADING = ("Ubuntu", 14, "bold")
FONT_SMALL = ("Ubuntu", 12)
FONT_CODE = ("JetBrains Mono", 13)
COMBO_RADIUS = 12
TAB_BODY_RADIUS = 12
TAB_BODY_INSET = 3


def combo(
    parent: ctk.CTkBaseClass,
    *,
    values: list[str] | tuple[str, ...],
    variable: tk.Variable | None = None,
    width: int = 160,
    height: int = 34,
    state: str = "normal",
    command=None,
    fill: bool = False,
) -> "RoundComboBox":
    from .widgets import RoundComboBox

    widget = RoundComboBox(
        parent,
        values=values,
        variable=variable,
        width=width,
        height=height,
        corner_radius=COMBO_RADIUS,
        state=state,
        command=command,
    )
    if fill:
        widget.pack(fill="x")
    return widget


def setup_theme() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    ctk.set_widget_scaling(1.0)
    ctk.set_window_scaling(1.0)


def card(parent: ctk.CTkBaseClass, *, fill: str = "x", pack: bool = True) -> ctk.CTkFrame:
    frame = ctk.CTkFrame(
        parent,
        fg_color=COLORS["surface"],
        corner_radius=10,
        border_width=1,
        border_color=COLORS["border_subtle"],
    )
    if pack:
        frame.pack(fill=fill, pady=(0, 10))
    return frame


def card_title(parent: ctk.CTkFrame, text: str) -> ctk.CTkFrame:
    ctk.CTkLabel(
        parent,
        text=text,
        font=FONT_HEADING,
        text_color=COLORS["fg"],
        anchor="w",
    ).pack(fill="x", padx=14, pady=(12, 6))
    body = ctk.CTkFrame(parent, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=14, pady=(0, 12))
    return body


def heading(parent: ctk.CTkBaseClass, text: str, **kwargs: Any) -> ctk.CTkLabel:
    label = ctk.CTkLabel(
        parent,
        text=text,
        font=FONT_HEADING,
        text_color=COLORS["fg"],
        anchor="w",
        **kwargs,
    )
    return label


def muted(parent: ctk.CTkBaseClass, text: str, **kwargs: Any) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent,
        text=text,
        font=FONT_SMALL,
        text_color=COLORS["fg_muted"],
        anchor="w",
        **kwargs,
    )


def btn_primary(parent: ctk.CTkBaseClass, text: str, command) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        height=36,
        corner_radius=8,
        fg_color=COLORS["accent"],
        hover_color=COLORS["accent_hover"],
        font=FONT_UI,
    )


def btn_secondary(parent: ctk.CTkBaseClass, text: str, command) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        height=32,
        corner_radius=8,
        fg_color=COLORS["surface_raised"],
        hover_color=COLORS["border"],
        border_width=1,
        border_color=COLORS["border"],
        text_color=COLORS["fg"],
        font=FONT_UI,
    )


def btn_danger(parent: ctk.CTkBaseClass, text: str, command) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        height=32,
        corner_radius=8,
        fg_color=COLORS["danger_bg"],
        hover_color="#52353a",
        text_color=COLORS["danger"],
        font=FONT_UI,
    )


def tab_button(parent: ctk.CTkBaseClass, text: str, command, *, active: bool = False) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        height=32,
        corner_radius=8,
        fg_color=COLORS["tab_active"] if active else COLORS["surface"],
        hover_color=COLORS["surface_raised"],
        border_width=2 if active else 1,
        border_color=COLORS["accent"] if active else COLORS["border"],
        text_color=COLORS["fg"] if active else COLORS["fg_muted"],
        font=FONT_UI,
    )


def textbox(parent: ctk.CTkBaseClass, *, height: int = 200, wrap: str = "word", monospace: bool = False) -> ctk.CTkTextbox:
    return ctk.CTkTextbox(
        parent,
        height=height,
        corner_radius=8,
        border_width=1,
        border_color=COLORS["border_subtle"],
        fg_color=COLORS["code"],
        text_color=COLORS["fg"],
        font=FONT_CODE if monospace else FONT_UI,
        wrap=wrap,
        activate_scrollbars=True,
    )


def style_treeview(root: tk.Misc) -> ttk.Style:
    """Dark ttk.Treeview for the results table (embedded in CTk)."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    c = COLORS
    style.configure(
        "Results.Treeview",
        background=c["input"],
        foreground=c["fg"],
        fieldbackground=c["input"],
        borderwidth=0,
        rowheight=30,
        font=FONT_UI,
    )
    style.configure(
        "Results.Treeview.Heading",
        background=c["surface_raised"],
        foreground=c["fg"],
        borderwidth=0,
        relief="flat",
        font=FONT_HEADING,
        padding=8,
        lightcolor=c["surface_raised"],
        darkcolor=c["surface_raised"],
    )
    style.map(
        "Results.Treeview",
        background=[("selected", c["select"])],
        foreground=[("selected", c["fg"])],
    )
    style.map(
        "Results.Treeview.Heading",
        background=[
            ("active", c["select"]),
            ("pressed", c["select"]),
            ("!active", c["surface_raised"]),
        ],
        foreground=[
            ("active", c["fg"]),
            ("pressed", c["fg"]),
            ("!active", c["fg"]),
        ],
        relief=[("pressed", "flat"), ("active", "flat")],
    )
    style.layout("Results.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    return style


def embed_treeview(parent: ctk.CTkBaseClass, columns: tuple[str, ...]) -> tuple[ttk.Treeview, tk.Frame]:
    host = tk.Frame(parent, bg=COLORS["input"], highlightthickness=0, bd=0)
    host.pack(fill="both", expand=True)
    style_treeview(parent.winfo_toplevel())
    tree = ttk.Treeview(host, columns=columns, show="headings", style="Results.Treeview")
    vsb = ttk.Scrollbar(host, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    return tree, host


def checkbox(parent: ctk.CTkBaseClass, text: str, variable: tk.Variable) -> ctk.CTkCheckBox:
    cb = ctk.CTkCheckBox(
        parent,
        text=text,
        variable=variable,
        font=FONT_UI,
        fg_color=COLORS["accent"],
        hover_color=COLORS["accent_hover"],
        border_color=COLORS["border"],
    )
    cb.pack(anchor="w")
    return cb


def mini_btn(parent: ctk.CTkBaseClass, text: str, command, *, width: int = 36) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        width=width,
        height=28,
        command=command,
        corner_radius=6,
        fg_color=COLORS["surface_raised"],
        hover_color=COLORS["border"],
        font=FONT_UI,
    )


# Legacy no-ops for any remaining imports
def apply_dark_theme(root: tk.Misc):
    setup_theme()
    return COLORS


def polish_widget_tree(root: tk.Misc, theme=None) -> None:
    pass


def add_scrolled_text(parent, **kwargs):
    raise NotImplementedError("Use theme.textbox() with CustomTkinter")


def style_text_widget(text, theme=None) -> None:
    pass
