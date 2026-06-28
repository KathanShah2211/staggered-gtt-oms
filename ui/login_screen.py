"""
ui/login_screen.py  —  Premium login & first-launch setup screen.
"""

from __future__ import annotations

import customtkinter as ctk
from typing import Callable

from core import encryption
from utils.logger import get_logger
from ui.theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BG_INPUT, BORDER_CARD, BORDER_DEFAULT,
    ACCENT, ACCENT_HOVER, ACCENT_LIGHT, ACCENT_SUBTLE,
    TEXT_BRIGHT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    SUCCESS, DANGER, WARN,
    font, BODY, BODY_BOLD, H1, H2, H3, CAPTION, CAPTION_BOLD,
)

log = get_logger(__name__)
MAX_ATTEMPTS = 5


class LoginScreen(ctk.CTkFrame):
    def __init__(self, master, state, on_success: Callable[[], None]) -> None:
        super().__init__(master, fg_color=BG_BASE, corner_radius=0)
        self._state      = state
        self._on_success = on_success
        self._attempts   = 0
        self._first      = not encryption.is_initialized()
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Outer centering frame ─────────────────────────────────
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(row=0, column=0)
        outer.grid_columnconfigure(0, weight=1)

        # ── Decorative backdrop strip ─────────────────────────────
        # Left-side accent column (purely cosmetic)
        root_grid = ctk.CTkFrame(self, fg_color="transparent")
        root_grid.grid(row=0, column=0, sticky="nsew")
        root_grid.grid_columnconfigure(0, weight=1)
        root_grid.grid_columnconfigure(1, weight=0)
        root_grid.grid_columnconfigure(2, weight=1)
        root_grid.grid_rowconfigure(0, weight=1)

        # Left decorative panel
        left_deco = ctk.CTkFrame(root_grid, fg_color="#070A14", corner_radius=0)
        left_deco.grid(row=0, column=0, sticky="nsew")
        self._build_left_deco(left_deco)

        # ── Card ─────────────────────────────────────────────────
        card_h = 520 if self._first else 440
        card = ctk.CTkFrame(
            root_grid,
            width=440,
            height=card_h,
            fg_color=BG_SURFACE,
            corner_radius=0,
            border_width=0,
        )
        card.grid(row=0, column=1, sticky="nsew")
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)

        self._build_card(card)

        # Right decorative panel
        right_deco = ctk.CTkFrame(root_grid, fg_color="#070A14", corner_radius=0)
        right_deco.grid(row=0, column=2, sticky="nsew")
        self._build_right_deco(right_deco)

    def _build_left_deco(self, parent: ctk.CTkFrame) -> None:
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(parent, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="", padx=60)

        ctk.CTkLabel(inner, text="⬡", font=font(120, "bold"),
                     text_color="#0D1A2E").pack()
        ctk.CTkLabel(inner, text="STAGGERED GTT",
                     font=font(11, "bold"), text_color="#1E3A5F").pack(pady=(8, 0))
        ctk.CTkLabel(inner, text="ORDER MANAGEMENT SYSTEM",
                     font=font(9), text_color="#152A44").pack()

    def _build_right_deco(self, parent: ctk.CTkFrame) -> None:
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(parent, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="", padx=40)

        for tag, color in [
            ("🔐  AES-256 Encrypted", "#1A3A5F"),
            ("🏦  ICICI Direct API",   "#1A3A5F"),
            ("💻  100% Local",         "#1A3A5F"),
            ("📋  Audit Logs",         "#1A3A5F"),
        ]:
            f = ctk.CTkFrame(inner, fg_color="#0B1628", corner_radius=8)
            f.pack(fill="x", pady=4, ipady=8, ipadx=12)
            ctk.CTkLabel(f, text=tag, font=font(11), text_color="#2A5A8F").pack(padx=16)

    def _build_card(self, card: ctk.CTkFrame) -> None:
        # Top accent bar
        ctk.CTkFrame(card, height=4, fg_color=ACCENT, corner_radius=0).pack(
            fill="x", side="top"
        )

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=48, pady=40)

        # Logo
        ctk.CTkLabel(inner, text="🔐", font=font(40)).pack()
        ctk.CTkLabel(
            inner, text="GTT Order Management",
            font=font(20, "bold"), text_color=TEXT_BRIGHT,
        ).pack(pady=(8, 4))
        ctk.CTkLabel(
            inner,
            text="Create master password" if self._first else "Enter your master password",
            font=font(12), text_color=TEXT_SECONDARY,
        ).pack(pady=(0, 28))

        # Password
        self._pw = ctk.CTkEntry(
            inner, placeholder_text="Master Password",
            show="●", height=46, width=344,
            fg_color=BG_INPUT, border_color=BORDER_DEFAULT,
            text_color=TEXT_BRIGHT, font=font(14), border_width=1,
        )
        self._pw.pack(pady=(0, 10))
        self._pw.bind("<Return>", lambda _: self._submit())
        self._pw.focus_set()

        # Confirm (first launch only)
        self._confirm: ctk.CTkEntry | None = None
        if self._first:
            self._confirm = ctk.CTkEntry(
                inner, placeholder_text="Confirm Password",
                show="●", height=46, width=344,
                fg_color=BG_INPUT, border_color=BORDER_DEFAULT,
                text_color=TEXT_BRIGHT, font=font(14), border_width=1,
            )
            self._confirm.pack(pady=(0, 10))
            self._confirm.bind("<Return>", lambda _: self._submit())

        # Error label
        self._err = ctk.CTkLabel(inner, text="", font=font(11),
                                  text_color=DANGER)
        self._err.pack(pady=(0, 8))

        # Submit button
        self._btn = ctk.CTkButton(
            inner,
            text="Set Password & Unlock" if self._first else "  Unlock  →",
            width=344, height=48,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=TEXT_BRIGHT, font=font(14, "bold"), corner_radius=10,
            command=self._submit,
        )
        self._btn.pack()

        # Footer note
        ctk.CTkLabel(
            inner, text="🔒  Credentials never leave this machine",
            font=font(10), text_color=TEXT_MUTED,
        ).pack(pady=(20, 0))

        if not self._first:
            ctk.CTkLabel(
                inner,
                text=f"Maximum {MAX_ATTEMPTS} attempts before auto-close",
                font=font(9), text_color=TEXT_MUTED,
            ).pack(pady=(4, 0))

    def _submit(self) -> None:
        pw = self._pw.get().strip()
        if not pw:
            self._err.configure(text="Password cannot be empty.")
            return

        if self._first:
            confirm = self._confirm.get().strip() if self._confirm else ""
            if len(pw) < 6:
                self._err.configure(text="Minimum 6 characters required.")
                return
            if pw != confirm:
                self._err.configure(text="Passwords do not match.")
                self._pw.delete(0, "end")
                self._confirm.delete(0, "end")  # type: ignore
                return
            try:
                encryption.setup_master_password(pw)
                self._on_success()
            except Exception as exc:
                self._err.configure(text=f"Setup failed: {exc}")
        else:
            self._attempts += 1
            if encryption.verify_and_unlock(pw):
                self._on_success()
            else:
                rem = MAX_ATTEMPTS - self._attempts
                if rem <= 0:
                    self._err.configure(text="Too many attempts — closing...")
                    self.after(1400, self.winfo_toplevel().destroy)
                else:
                    self._err.configure(
                        text=f"Incorrect password — {rem} attempt(s) left."
                    )
                    self._pw.delete(0, "end")
                    self._pw.focus_set()
