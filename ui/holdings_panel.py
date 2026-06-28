"""
ui/holdings_panel.py  —  Premium holdings viewer.
"""
from __future__ import annotations
import threading
import customtkinter as ctk
from core.breeze_client import fetch_holdings, BreezeAPIError
from utils.logger import get_logger
from ui.theme import *

log = get_logger(__name__)


class HoldingsPanel(ctk.CTkFrame):
    def __init__(self, master, app, state) -> None:
        super().__init__(master, fg_color=BG_BASE, corner_radius=0)
        self._app = app
        self._state = state
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Header ────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 0))
        
        titles = ctk.CTkFrame(hdr, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(titles, text="Portfolio Holdings", font=font(22, "bold"),
                     text_color=TEXT_BRIGHT).pack(anchor="w")
        
        self._status_l = ctk.CTkLabel(titles, text="Live view from ICICI Direct NSE demat account",
                                      font=font(11), text_color=TEXT_SECONDARY)
        self._status_l.pack(anchor="w", pady=(2, 0))

        self._fetch_btn = primary_btn(hdr, text="🔄  Refresh Data", command=self._fetch, width=150)
        self._fetch_btn.pack(side="right")

        # ── Table Card ────────────────────────────────────────────
        c = card(self)
        c.grid(row=2, column=0, sticky="nsew", padx=32, pady=(16, 28))
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(1, weight=1)

        th = ctk.CTkFrame(c, fg_color=BG_HEADER, corner_radius=0, height=44)
        th.grid(row=0, column=0, sticky="ew")
        th.grid_propagate(False)
        
        for t, w in [("Stock Code", 220), ("ISIN", 160), ("Total Qty", 100), ("Free Qty", 100), ("Exchange", 90), ("", 150)]:
            ctk.CTkLabel(th, text=t, font=font(11, "bold"), text_color=TEXT_SECONDARY,
                         width=w, anchor="w").pack(side="left", padx=16, pady=10)

        self._scroll = ctk.CTkScrollableFrame(
            c, fg_color="transparent", scrollbar_button_color=BORDER_DEFAULT,
            scrollbar_button_hover_color=ACCENT
        )
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        if self._state.holdings:
            self._render(self._state.holdings)
        else:
            self._msg("Click 'Refresh Data' to load your portfolio.")

    def _fetch(self) -> None:
        if not self._state.is_connected:
            self._status_l.configure(text="⚠️  Not connected. Go to Session panel.", text_color=WARN); return
        
        self._fetch_btn.configure(state="disabled", text="⏳  Fetching...")
        self._status_l.configure(text="Fetching latest holdings...", text_color=TEXT_SECONDARY)

        def _bg() -> None:
            try:
                h = fetch_holdings(self._state.breeze_instance)
                self._state.holdings = h
                self.after(0, self._render, h)
                self.after(0, lambda: self._status_l.configure(text=f"✅  Loaded {len(h)} items.", text_color=SUCCESS))
            except Exception as e:
                self.after(0, lambda: self._status_l.configure(text=f"🔴  Error: {e}", text_color=DANGER))
            finally:
                self.after(0, lambda: self._fetch_btn.configure(state="normal", text="🔄  Refresh Data"))
        threading.Thread(target=_bg, daemon=True).start()

    def _msg(self, text: str) -> None:
        for w in self._scroll.winfo_children(): w.destroy()
        ctk.CTkLabel(self._scroll, text=text, font=font(13), text_color=TEXT_SECONDARY).pack(pady=60)

    def _render(self, h: list[dict]) -> None:
        for w in self._scroll.winfo_children(): w.destroy()
        if not h:
            self._msg("Portfolio is empty."); return
            
        for i, item in enumerate(h):
            bg = BG_ROW_A if i % 2 == 0 else BG_ROW_B
            r = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=8)
            r.pack(fill="x", padx=4, pady=3)

            def _lbl(t, w, c=TEXT_BRIGHT, f=BODY()):
                ctk.CTkLabel(r, text=str(t), font=f, text_color=c, width=w, anchor="w").pack(side="left", padx=16, pady=12)

            _lbl(item.get("stock_code"), 220, ACCENT_LIGHT, BODY_BOLD())
            _lbl(item.get("isin"),       160, TEXT_SECONDARY, MONO_SM())
            _lbl(item.get("quantity",0), 100)
            _lbl(item.get("free_qty",0), 100, SUCCESS)
            _lbl(item.get("exchange"),    90, TEXT_SECONDARY)

            ctk.CTkButton(
                r, text="⚙  Configure GTT", width=130, height=32,
                fg_color=ACCENT_SUBTLE, hover_color=ACCENT, text_color=ACCENT_LIGHT,
                font=font(11, "bold"), corner_radius=6,
                command=lambda x=item: self._go(x)
            ).pack(side="left", padx=10)
            # ── AI Analyze shortcut ────────────────────────────────
            ctk.CTkButton(
                r, text="🧠 AI Analyze", width=110, height=32,
                fg_color="transparent", hover_color=ACCENT_GLOW,
                border_width=1, border_color=ACCENT,
                text_color=ACCENT_LIGHT, font=font(11, "bold"), corner_radius=6,
                command=lambda x=item: self._go_ai(x)
            ).pack(side="left", padx=(0, 10))

    def _go(self, item: dict) -> None:
        self._state.selected_stock = item.get("stock_code")
        self._state.selected_exchange = item.get("exchange", "NSE")
        self._state.selected_free_qty = item.get("free_qty", 0)
        self._state.cfg_total_shares = item.get("free_qty", 0)
        self._app.show_panel("config")

    def _go_ai(self, item: dict) -> None:
        """Navigate directly to the AI Analysis panel for this holding."""
        self._state.selected_stock    = item.get("stock_code")
        self._state.selected_exchange = item.get("exchange", "NSE")
        self._state.selected_free_qty = item.get("free_qty", 0)
        # Clear stale cached analysis for a different stock
        self._state.ai_indicators    = {}
        self._state.ai_analysis_text = ""
        self._app.show_panel("analysis")
