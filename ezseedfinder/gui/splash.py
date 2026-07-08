"""Startup splash and in-tab loading overlays."""

from __future__ import annotations

import customtkinter as ctk

from .theme import COLORS, FONT_HEADING, FONT_SMALL, FONT_UI, TAB_BODY_INSET, TAB_BODY_RADIUS


class StartupOverlay(ctk.CTkFrame):
    """Full-window overlay shown while the GUI builds."""

    def __init__(self, parent: ctk.CTk, *, version: str) -> None:
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            center,
            text="EZ Seed Finder",
            font=("Ubuntu", 28, "bold"),
            text_color=COLORS["fg"],
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            center,
            text=f"v{version}",
            font=FONT_SMALL,
            text_color=COLORS["fg_muted"],
        ).pack(pady=(0, 28))

        self._status = ctk.CTkLabel(
            center,
            text="Starting…",
            font=FONT_UI,
            text_color=COLORS["fg_muted"],
        )
        self._status.pack(pady=(0, 10))

        self._bar = ctk.CTkProgressBar(
            center,
            width=360,
            height=12,
            corner_radius=6,
            progress_color=COLORS["accent"],
            fg_color=COLORS["surface_raised"],
        )
        self._bar.set(0)
        self._bar.pack()

    def set_progress(self, value: float, message: str) -> None:
        self._bar.set(max(0.0, min(1.0, value)))
        self._status.configure(text=message)
        self.lift()
        self.update_idletasks()


class TabLoadOverlay(ctk.CTkFrame):
    """Lightweight overlay while a lazy tab panel is built."""

    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(
            parent,
            fg_color=COLORS["tab_body"],
            corner_radius=TAB_BODY_RADIUS - TAB_BODY_INSET,
            border_width=0,
        )
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            inner,
            text="Loading panel…",
            font=FONT_HEADING,
            text_color=COLORS["fg_muted"],
        ).pack(pady=(0, 8))

        self._bar = ctk.CTkProgressBar(
            inner,
            width=200,
            height=8,
            corner_radius=4,
            progress_color=COLORS["accent"],
            fg_color=COLORS["surface_raised"],
        )
        self._bar.set(0.2)
        self._bar.pack()
        self._pulse = 0.2
        self._pulse_dir = 1
        self._animate()

    def _animate(self) -> None:
        if not self.winfo_exists():
            return
        self._pulse += 0.08 * self._pulse_dir
        if self._pulse >= 0.9:
            self._pulse_dir = -1
        elif self._pulse <= 0.15:
            self._pulse_dir = 1
        self._bar.set(self._pulse)
        self.after(60, self._animate)
