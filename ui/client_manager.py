"""
ui/client_manager.py  —  Premium client profile manager.
"""
from __future__ import annotations
import sqlite3
import customtkinter as ctk
from tkinter import messagebox
from core import database
from utils.logger import get_logger
from ui.theme import *

log = get_logger(__name__)


class ClientManagerPanel(ctk.CTkFrame):
    def __init__(self, master, app, state) -> None:
        super().__init__(master, fg_color=BG_BASE, corner_radius=0)
        self._app = app
        self._state = state
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Header ────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 0))
        ctk.CTkLabel(hdr, text="Client Profiles", font=font(22, "bold"),
                     text_color=TEXT_BRIGHT).pack(side="left")
        ctk.CTkLabel(hdr, text="  Encrypted API credentials for each ICICI Direct account",
                     font=font(11), text_color=TEXT_SECONDARY).pack(side="left", pady=(6, 0))

        # ── Body ─────────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=32, pady=20)
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self._build_form(body)
        self._build_table(body)

    # ── Form ──────────────────────────────────────────────────────

    def _build_form(self, parent) -> None:
        card = ctk.CTkFrame(parent, fg_color=BG_SURFACE, corner_radius=14,
                             border_width=1, border_color=BORDER_CARD, width=340)
        card.grid(row=0, column=0, sticky="ns", padx=(0, 20))
        card.grid_propagate(False)

        # Card header strip
        strip = ctk.CTkFrame(card, fg_color=ACCENT_SUBTLE, corner_radius=0, height=48)
        strip.pack(fill="x")
        strip.pack_propagate(False)
        ctk.CTkLabel(strip, text="  ➕  Add New Client", font=font(13, "bold"),
                     text_color=ACCENT_LIGHT, anchor="w").pack(fill="both", expand=True, padx=16)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=20)

        def row(lbl: str, ph: str, show: str = "") -> ctk.CTkEntry:
            ctk.CTkLabel(inner, text=lbl, font=font(11, "bold"),
                         text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=(10, 3))
            e = ctk.CTkEntry(inner, placeholder_text=ph, show=show,
                              height=42, fg_color=BG_INPUT, border_color=BORDER_DEFAULT,
                              text_color=TEXT_BRIGHT, font=font(13), border_width=1)
            e.pack(fill="x")
            return e

        self._name_e   = row("Account Name",  "e.g. John — ICICI Primary")
        self._appkey_e = row("App Key",        "Paste App Key here",    "●")
        self._seckey_e = row("Secret Key",     "Paste Secret Key here", "●")

        self._form_msg = ctk.CTkLabel(inner, text="", font=font(11),
                                       text_color=DANGER)
        self._form_msg.pack(pady=(8, 0))

        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(fill="x", pady=(12, 0))
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_row, text="💾 Save", height=38,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=TEXT_BRIGHT, font=font(12, "bold"), corner_radius=8,
            command=self._save,
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        
        ctk.CTkButton(
            btn_row, text="✨ Mock Account", height=38,
            fg_color=SUCCESS_DIM, hover_color=SUCCESS,
            text_color=TEXT_BRIGHT, font=font(12, "bold"), corner_radius=8,
            command=self._add_mock_account,
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

    def _add_mock_account(self) -> None:
        try:
            database.add_client("Test Account (Mock)", "MOCK", "MOCK_SECRET")
            self._form_msg.configure(text="✅  Mock account added.", text_color=SUCCESS)
            self._refresh_table()
        except sqlite3.IntegrityError:
            self._form_msg.configure(text="Mock account already exists.", text_color=WARN)
        except Exception as exc:
            self._form_msg.configure(text=str(exc), text_color=DANGER)

    # ── Table ─────────────────────────────────────────────────────

    def _build_table(self, parent) -> None:
        self._table_card = ctk.CTkFrame(parent, fg_color=BG_SURFACE, corner_radius=14,
                                         border_width=1, border_color=BORDER_CARD)
        self._table_card.grid(row=0, column=1, sticky="nsew")
        self._table_card.grid_columnconfigure(0, weight=1)
        self._table_card.grid_rowconfigure(1, weight=1)

        # Table header
        hdr = ctk.CTkFrame(self._table_card, fg_color=BG_HEADER, corner_radius=0, height=44)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        for txt, w in [("Client Name", 300), ("Created", 200), ("", 120)]:
            ctk.CTkLabel(hdr, text=txt, font=font(11, "bold"), text_color=TEXT_SECONDARY,
                         width=w, anchor="w").pack(side="left", padx=16, pady=10)

        self._scroll = ctk.CTkScrollableFrame(
            self._table_card, fg_color="transparent",
            scrollbar_button_color=BORDER_DEFAULT,
            scrollbar_button_hover_color=ACCENT,
        )
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self._refresh_table()

    def _refresh_table(self) -> None:
        for w in self._scroll.winfo_children():
            w.destroy()
        clients = database.get_all_clients()
        if not clients:
            ctk.CTkLabel(self._scroll, text="No clients yet. Add one using the form →",
                         font=font(13), text_color=TEXT_SECONDARY).pack(pady=50)
            return
        for i, c in enumerate(clients):
            bg = BG_ROW_A if i % 2 == 0 else BG_ROW_B
            row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=8)
            row.pack(fill="x", padx=4, pady=3)
            ctk.CTkLabel(row, text=c["client_name"], font=font(13),
                         text_color=TEXT_BRIGHT, width=300, anchor="w").pack(side="left", padx=16, pady=12)
            ctk.CTkLabel(row, text=str(c.get("created_at",""))[:16],
                         font=font(11), text_color=TEXT_SECONDARY, width=200, anchor="w").pack(side="left", padx=8)
            ctk.CTkButton(
                row, text="🗑 Delete", width=100, height=32,
                fg_color=DANGER_BG, hover_color=DANGER_DIM,
                border_width=1, border_color=DANGER_DIM,
                text_color=DANGER, font=font(11, "bold"), corner_radius=6,
                command=lambda n=c["client_name"]: self._delete(n),
            ).pack(side="left", padx=12)

    def _save(self) -> None:
        name   = self._name_e.get().strip()
        appkey = self._appkey_e.get().strip()
        seckey = self._seckey_e.get().strip()
        for val, msg in [(name, "Account name required."),
                          (appkey, "App Key required."), (seckey, "Secret Key required.")]:
            if not val:
                self._form_msg.configure(text=msg, text_color=DANGER); return
        try:
            database.add_client(name, appkey, seckey)
            self._name_e.delete(0, "end"); self._appkey_e.delete(0, "end"); self._seckey_e.delete(0, "end")
            self._form_msg.configure(text=f"✅  '{name}' saved.", text_color=SUCCESS)
            self._refresh_table()
        except sqlite3.IntegrityError:
            self._form_msg.configure(text=f"'{name}' already exists.", text_color=DANGER)
        except Exception as exc:
            self._form_msg.configure(text=str(exc), text_color=DANGER)

    def _delete(self, name: str) -> None:
        if messagebox.askyesno("Delete Client",
                               f"Permanently delete client '{name}' and their API credentials?",
                               icon="warning"):
            database.delete_client(name)
            self._refresh_table()
