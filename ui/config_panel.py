"""
ui/config_panel.py  —  Premium GTT configuration panel.
"""
from __future__ import annotations
import customtkinter as ctk
from core.gtt_engine import calculate_orders
from utils.logger import get_logger
from ui.theme import *

log = get_logger(__name__)


class ConfigPanel(ctk.CTkFrame):
    def __init__(self, master, app, state) -> None:
        super().__init__(master, fg_color=BG_BASE, corner_radius=0)
        self._app = app
        self._state = state
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 0))
        ctk.CTkLabel(hdr, text="Configure GTT Orders", font=font(22, "bold"),
                     text_color=TEXT_BRIGHT).pack(side="left")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=32, pady=20)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        c = card(body, width=580, height=620)
        c.grid(row=0, column=0)
        c.grid_propagate(False)

        # Stock header strip
        stock = self._state.selected_stock or "— No stock selected —"
        exc   = self._state.selected_exchange or "NSE"
        qty   = self._state.selected_free_qty or 0

        strip = ctk.CTkFrame(c, fg_color=ACCENT_SUBTLE, corner_radius=0, height=56)
        strip.pack(fill="x")
        strip.pack_propagate(False)
        ctk.CTkLabel(strip, text=f"  📈  {stock}", font=font(16, "bold"), text_color=ACCENT_LIGHT, anchor="w").pack(side="left", padx=16)
        ctk.CTkLabel(strip, text=f"{exc}   |   Free: {qty} shares", font=font(12), text_color=TEXT_SECONDARY).pack(side="right", padx=24)

        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=40, pady=24)

        self._fields = {}
        defs = [
            ("total_shares", "Total Shares",   str(qty), "Integer"),
            ("batch_size",   "Batch Size",     "10",     "Integer"),
            ("base_trigger", "Base Trigger ₹", "",       "Float"),
            ("price_gap",    "Price Gap ₹",    "1.0",    "Float"),
            ("limit_offset", "Limit Offset ₹", "0.05",   "Float"),
        ]

        for k, lbl, df, ht in defs:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=6)
            row.grid_columnconfigure(1, weight=1)
            
            ctk.CTkLabel(row, text=lbl, font=font(12, "bold"), text_color=TEXT_BRIGHT, width=120, anchor="w").grid(row=0, column=0, sticky="w")
            
            e = form_entry(row, width=320)
            e.grid(row=0, column=1, sticky="e")
            
            val = getattr(self._state, f"cfg_{k}")
            if val not in (None, 0, 0.0, ""):
                e.insert(0, str(val))
            elif df:
                e.insert(0, df)
                
            err = ctk.CTkLabel(inner, text="", font=font(10), text_color=DANGER, height=14)
            err.pack(fill="x", anchor="e", padx=(120, 0))
            
            self._fields[k] = (e, err)

        nav = ctk.CTkFrame(inner, fg_color="transparent")
        nav.pack(fill="x", pady=(24, 0))
        ghost_btn(nav, text="← Holdings", command=lambda: self._app.show_panel("holdings"), width=140).pack(side="left")
        # ── AI Suggest shortcut ────────────────────────────────────
        ctk.CTkButton(
            nav, text="🧠  AI Suggest", width=160, height=40,
            fg_color=ACCENT_SUBTLE, hover_color=ACCENT_GLOW,
            border_width=1, border_color=ACCENT,
            text_color=ACCENT_LIGHT, font=font(12, "bold"), corner_radius=8,
            command=lambda: self._app.show_panel("suggest"),
        ).pack(side="left", padx=(12, 0))
        primary_btn(nav, text="Preview Orders →", command=self._preview, width=220).pack(side="right")

    def _err(self, k: str, m: str) -> None:
        self._fields[k][1].configure(text=m)

    def _clr(self) -> None:
        for k in self._fields: self._fields[k][1].configure(text="")

    def _preview(self) -> None:
        self._clr()
        ok = True
        def get_i(k):
            try: return int(self._fields[k][0].get().strip())
            except ValueError: self._err(k, "Must be an integer"); return None
        def get_f(k):
            try: return float(self._fields[k][0].get().strip())
            except ValueError: self._err(k, "Must be a number"); return None

        tot = get_i("total_shares")
        bs  = get_i("batch_size")
        tr  = get_f("base_trigger")
        pg  = get_f("price_gap")
        lo  = get_f("limit_offset")

        if tot is None or tot <= 0: self._err("total_shares", "Must be > 0"); ok=False
        if bs is None or bs <= 0: self._err("batch_size", "Must be > 0"); ok=False
        elif tot and bs > tot: self._err("batch_size", "Cannot exceed total"); ok=False
        if tr is None or tr <= 0: self._err("base_trigger", "Must be > 0"); ok=False
        if pg is None: ok=False
        if lo is None: ok=False

        if not ok: return

        self._state.cfg_total_shares = tot
        self._state.cfg_batch_size = bs
        self._state.cfg_base_trigger = tr
        self._state.cfg_price_gap = pg
        self._state.cfg_limit_offset = lo

        try:
            self._state.planned_orders = calculate_orders(
                self._state.selected_stock or "", self._state.selected_exchange or "NSE",
                tot, bs, tr, pg, lo, "sell"
            )
            self._app.show_panel("preview")
        except Exception as e:
            self._err("batch_size", str(e))
