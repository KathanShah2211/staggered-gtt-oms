"""
ui/logs_panel.py  —  Premium logs and history panel.
"""
from __future__ import annotations
import csv
import customtkinter as ctk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox
from core import database
from utils.logger import get_logger
from ui.theme import *

log = get_logger(__name__)
_EXP = Path(__file__).resolve().parent.parent / "data" / "logs"


class LogsPanel(ctk.CTkFrame):
    def __init__(self, master, app, state) -> None:
        super().__init__(master, fg_color=BG_BASE, corner_radius=0)
        self._app = app
        self._state = state
        self._logs = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 0))
        ctk.CTkLabel(hdr, text="Order History", font=font(22, "bold"), text_color=TEXT_BRIGHT).pack(side="left")
        
        ghost_btn(hdr, text="📥  Export CSV", command=self._export, width=140).pack(side="right")

        # ── Filter Bar ────────────────────────────────────────────
        fb = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=10, border_width=1, border_color=BORDER_CARD)
        fb.grid(row=1, column=0, sticky="ew", padx=32, pady=(16, 0))
        
        inner = ctk.CTkFrame(fb, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(inner, text="Client", font=font(11, "bold"), text_color=TEXT_SECONDARY).pack(side="left", padx=(0, 8))
        
        opts = ["All Clients"] + database.get_distinct_clients_from_logs()
        self._cl = ctk.StringVar(value="All Clients")
        ctk.CTkOptionMenu(inner, variable=self._cl, values=opts, width=180, height=36,
                          fg_color=BG_INPUT, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
                          text_color=TEXT_BRIGHT, font=font(12)).pack(side="left", padx=(0, 24))

        ctk.CTkLabel(inner, text="Date", font=font(11, "bold"), text_color=TEXT_SECONDARY).pack(side="left", padx=(0, 8))
        self._dt = form_entry(inner, placeholder="YYYY-MM-DD", width=120, height=36)
        self._dt.pack(side="left", padx=(0, 16))

        primary_btn(inner, text="Filter", command=self._apply, width=100, height=36).pack(side="left", padx=(0, 8))
        ghost_btn(inner, text="Clear", command=self._clr, width=80, height=36).pack(side="left")

        self._cnt = ctk.CTkLabel(inner, text="", font=font(11, "bold"), text_color=ACCENT)
        self._cnt.pack(side="right", padx=16)

        # ── Table ─────────────────────────────────────────────────
        c = card(self)
        c.grid(row=2, column=0, sticky="nsew", padx=32, pady=(16, 24))
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(1, weight=1)

        th = ctk.CTkFrame(c, fg_color=BG_HEADER, corner_radius=0, height=44)
        th.grid(row=0, column=0, sticky="ew")
        th.grid_propagate(False)
        for t, w in [("ID", 50), ("Client", 140), ("Stock", 90), ("Batch", 60), ("Trigger ₹", 100), ("Qty", 60), ("Status", 90), ("Timestamp", 160)]:
            ctk.CTkLabel(th, text=t, font=font(11, "bold"), text_color=TEXT_SECONDARY, width=w, anchor="w").pack(side="left", padx=8, pady=10)

        self._scroll = ctk.CTkScrollableFrame(c, fg_color="transparent", scrollbar_button_color=BORDER_DEFAULT, scrollbar_button_hover_color=ACCENT)
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        self._apply()

    def _apply(self) -> None:
        c = self._cl.get()
        d = self._dt.get().strip()
        self._logs = database.get_order_logs(None if c == "All Clients" else c, d if d else None)
        self._cnt.configure(text=f"{len(self._logs)} records")
        
        for w in self._scroll.winfo_children(): w.destroy()
        if not self._logs:
            ctk.CTkLabel(self._scroll, text="No records match this filter.", font=font(13), text_color=TEXT_SECONDARY).pack(pady=40)
            return

        for i, row in enumerate(self._logs):
            bg = BG_ROW_A if i % 2 == 0 else BG_ROW_B
            r = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=8)
            r.pack(fill="x", padx=4, pady=3)

            st = (row.get("status") or "").upper()
            sc = SUCCESS if st=="SUCCESS" else DANGER if st=="FAILED" else WARN

            def _c(txt, w, clr=TEXT_BRIGHT): ctk.CTkLabel(r, text=str(txt)[:30], font=font(12), text_color=clr, width=w, anchor="w").pack(side="left", padx=8, pady=10)

            _c(row.get("id"), 50, TEXT_SECONDARY)
            _c(row.get("client_name"), 140)
            _c(row.get("stock_code"), 90, ACCENT_LIGHT)
            _c(row.get("batch_number"), 60)
            _c(f"₹{row.get('trigger_price', 0):.2f}", 100)
            _c(row.get("quantity"), 60)
            _c(st, 90, sc)
            _c(str(row.get("timestamp"))[:19], 160, TEXT_SECONDARY)

    def _clr(self) -> None:
        self._cl.set("All Clients")
        self._dt.delete(0, "end")
        self._apply()

    def _export(self) -> None:
        if not self._logs: messagebox.showinfo("Export", "No records to export."); return
        _EXP.mkdir(parents=True, exist_ok=True)
        out = _EXP / f"gtt_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["id","client_name","stock_code","batch_number","trigger_price","quantity","status","response_json","timestamp"], extrasaction="ignore")
                w.writeheader(); w.writerows(self._logs)
            messagebox.showinfo("Success", f"Exported {len(self._logs)} records to:\n{out}")
        except Exception as e: messagebox.showerror("Error", str(e))
