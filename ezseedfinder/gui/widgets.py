"""Custom rounded dropdown — CTkComboBox uses a square native menu on Linux."""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable

import customtkinter as ctk

from .theme import COLORS, FONT_UI


class IndeterminateProgressBar(ctk.CTkFrame):
    """Looping marquee bar for in-progress search (no snap-back)."""

    def __init__(
        self,
        master: Any,
        *,
        width: int = 180,
        height: int = 10,
    ) -> None:
        super().__init__(
            master,
            width=width,
            height=height,
            fg_color=COLORS["surface_raised"],
            corner_radius=height // 2,
            border_width=0,
        )
        self.pack_propagate(False)
        self.grid_propagate(False)
        self._height = height
        self._track_w = width
        self._chunk_frac = 0.38
        self._pos = -self._chunk_frac
        self._speed = 0.018
        self._running = False
        self._after_id: str | None = None

        self._chunk = ctk.CTkFrame(
            self,
            height=max(4, height - 2),
            fg_color=COLORS["accent"],
            corner_radius=max(2, (height - 2) // 2),
            border_width=0,
        )
        self.bind("<Configure>", self._on_resize, add="+")

    def _on_resize(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        w = event.width
        if w < 24 or abs(w - self._track_w) < 2:
            return
        self._track_w = w
        self._chunk.configure(height=max(4, self._height - 2))
        if self._running:
            self._place_chunk()

    def _place_chunk(self) -> None:
        self._chunk.place(
            relx=self._pos,
            rely=0.5,
            anchor="w",
            relwidth=self._chunk_frac,
            relheight=0.75,
        )

    def start(self) -> None:
        self._running = True
        self._pos = -self._chunk_frac
        self._track_w = max(self.winfo_width(), self._track_w)
        self._chunk.configure(height=max(4, self._height - 2))
        self._place_chunk()
        self._tick()

    def stop(self) -> None:
        self._running = False
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        self._chunk.place_forget()

    def pause(self) -> None:
        self._running = False
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def resume(self) -> None:
        if self._running:
            return
        self._running = True
        self._tick()

    def _tick(self) -> None:
        if not self._running:
            return
        self._pos += self._speed
        # Reset only once the chunk has fully exited the right edge.
        if self._pos > 1.0:
            self._pos = -self._chunk_frac
        self._place_chunk()
        self._after_id = self.after(40, self._tick)


class RoundComboBox(ctk.CTkFrame):
    """Read-only combobox with a rounded CTk popup menu."""

    def __init__(
        self,
        master: Any,
        values: list[str] | tuple[str, ...] | None = None,
        variable: tk.StringVar | None = None,
        width: int = 160,
        height: int = 34,
        corner_radius: int = 12,
        command: Callable[[str], Any] | None = None,
        state: str = "normal",
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", width=width, height=height)
        self._values = list(values or [])
        self._variable = variable or tk.StringVar(
            value=self._values[0] if self._values else ""
        )
        self._command = command
        self._state = state
        self._corner_radius = corner_radius
        self._popup: ctk.CTkToplevel | None = None
        self._outside_bind: str | None = None

        self._button = ctk.CTkButton(
            self,
            textvariable=self._variable,
            command=self._toggle,
            height=height,
            corner_radius=corner_radius,
            fg_color=COLORS["input"],
            hover_color=COLORS["surface_raised"],
            border_width=1,
            border_color=COLORS["border_subtle"],
            text_color=COLORS["fg"],
            anchor="w",
            font=FONT_UI,
        )
        self._button.pack(fill="both", expand=True, padx=0, pady=0)
        if self._state == "disabled":
            self._button.configure(state="disabled")

    def _toggle(self) -> None:
        if self._state == "disabled" or not self._values:
            return
        if self._popup is not None and self._popup.winfo_exists():
            self._close()
        else:
            self._open()

    def _open(self) -> None:
        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 4
        width = max(self.winfo_width(), 180)
        row_h = 34
        height = min(len(self._values) * row_h + 12, 280)

        popup = ctk.CTkToplevel(self)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(fg_color=COLORS["input"])
        popup.geometry(f"{width}x{height}+{x}+{y}")

        shell = ctk.CTkFrame(
            popup,
            corner_radius=self._corner_radius,
            border_width=1,
            border_color=COLORS["border"],
            fg_color=COLORS["input"],
        )
        shell.pack(fill="both", expand=True)

        list_frame = ctk.CTkScrollableFrame(
            shell,
            fg_color="transparent",
            corner_radius=self._corner_radius - 2,
            scrollbar_button_color=COLORS["surface_raised"],
            scrollbar_button_hover_color=COLORS["border"],
        )
        list_frame.pack(fill="both", expand=True, padx=6, pady=6)

        current = self._variable.get()
        for value in self._values:
            selected = value == current
            btn = ctk.CTkButton(
                list_frame,
                text=value,
                anchor="w",
                height=row_h - 4,
                corner_radius=max(self._corner_radius - 4, 6),
                fg_color=COLORS["select"] if selected else "transparent",
                hover_color=COLORS["select"],
                text_color=COLORS["fg"],
                font=FONT_UI,
                command=lambda v=value: self._pick(v),
            )
            btn.pack(fill="x", pady=1)

        popup.deiconify()
        self._popup = popup
        root = self.winfo_toplevel()
        self._outside_bind = root.bind("<Button-1>", self._on_outside_click, add="+")

    def _on_outside_click(self, event: tk.Event) -> None:
        if self._popup is None or not self._popup.winfo_exists():
            self._close()
            return
        widget = event.widget
        while widget is not None:
            if widget == self._popup or widget == self:
                return
            widget = widget.master if hasattr(widget, "master") else None
        self._close()

    def _pick(self, value: str) -> None:
        self._variable.set(value)
        self._close()
        if self._command is not None:
            self._command(value)

    def _close(self) -> None:
        if self._outside_bind is not None:
            try:
                self.winfo_toplevel().unbind("<Button-1>", self._outside_bind)
            except tk.TclError:
                pass
            self._outside_bind = None
        if self._popup is not None and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None

    def configure(self, **kwargs: Any) -> None:
        if "values" in kwargs:
            self._values = list(kwargs.pop("values"))
        if "variable" in kwargs:
            self._variable = kwargs.pop("variable")
            self._button.configure(textvariable=self._variable)
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            self._button.configure(state=self._state)
        if "width" in kwargs:
            super().configure(width=kwargs.pop("width"))
        if "height" in kwargs:
            h = kwargs.pop("height")
            self._button.configure(height=h)
        if kwargs:
            super().configure(**kwargs)

    config = configure

    def cget(self, attribute_name: str) -> Any:
        if attribute_name == "values":
            return list(self._values)
        if attribute_name == "variable":
            return self._variable
        if attribute_name == "state":
            return self._state
        return super().cget(attribute_name)

    def get(self) -> str:
        return self._variable.get()

    def set(self, value: str) -> None:
        self._variable.set(value)

    def destroy(self) -> None:
        self._close()
        super().destroy()
