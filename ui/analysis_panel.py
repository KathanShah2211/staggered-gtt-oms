"""
ui/analysis_panel.py
====================
AI Stock Analysis panel.

Two-column layout:
  Left  — scrollable technical indicators grouped by category.
  Right — AI analysis text returned by Claude via Bedrock.

All heavy work (OHLC fetch, indicator compute, Claude call) runs in a
daemon thread so the UI never blocks.
Results are cached in AppState.ai_indicators and AppState.ai_analysis_text
so switching panels doesn't force a re-fetch.
"""

from __future__ import annotations

import threading
import customtkinter as ctk
from typing import Any

from core import market_data, ai_engine
from utils.logger import get_logger
from ui.theme import *

log = get_logger(__name__)


class AnalysisPanel(ctk.CTkFrame):

    def __init__(self, master: Any, app: Any, state: Any) -> None:
        super().__init__(master, fg_color=BG_BASE, corner_radius=0)
        self._app   = app
        self._state = state
        self._current_stock: str | None = None
        self._build_ui()

    # ─────────────────────────────────────────────────────────────
    # Layout construction
    # ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Row 0: Page header ────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 0))
        ctk.CTkLabel(
            hdr, text="AI Stock Analysis", font=font(22, "bold"),
            text_color=TEXT_BRIGHT,
        ).pack(side="left")
        ctk.CTkLabel(
            hdr, text="  Technical indicators + Claude AI insights",
            font=font(11), text_color=TEXT_SECONDARY,
        ).pack(side="left", pady=(6, 0))

        # ── Row 1: Controls bar ───────────────────────────────────
        ctrl = ctk.CTkFrame(
            self, fg_color=BG_SURFACE, corner_radius=10,
            border_width=1, border_color=BORDER_CARD,
        )
        ctrl.grid(row=1, column=0, sticky="ew", padx=32, pady=(16, 0))
        ctrl.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(ctrl, text="Stock", font=font(11, "bold"),
                     text_color=TEXT_SECONDARY).grid(row=0, column=0, padx=(16, 8), pady=14)

        stocks = [h.get("stock_code", "") for h in self._state.holdings if h.get("stock_code")]
        if not stocks:
            stocks = ["— Fetch holdings first —"]
        if self._state.selected_stock and self._state.selected_stock in stocks:
            default = self._state.selected_stock
        else:
            default = stocks[0]

        self._stock_var = ctk.StringVar(value=default)
        self._dd = ctk.CTkOptionMenu(
            ctrl, variable=self._stock_var, values=stocks,
            width=220, height=38,
            fg_color=BG_INPUT, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            text_color=TEXT_BRIGHT, font=font(13),
            command=self._on_stock_change,
        )
        self._dd.grid(row=0, column=1, sticky="w", padx=(0, 16), pady=14)

        self._status_l = ctk.CTkLabel(
            ctrl, text="Select a stock and click Analyze.",
            font=font(11), text_color=TEXT_SECONDARY,
        )
        self._status_l.grid(row=0, column=2, sticky="ew", padx=8)

        # Model badge — informs user which model tier is running
        ctk.CTkLabel(
            ctrl, text="🤖  Gemini 3.1 Pro",
            font=font(10), text_color=TEXT_SECONDARY,
        ).grid(row=0, column=3, padx=(0, 8))

        self._analyze_btn = primary_btn(
            ctrl, text="🧠  Analyze Stock", command=self._start_analysis,
            width=180, height=38,
        )
        self._analyze_btn.grid(row=0, column=4, padx=(8, 16), pady=14)

        # ── Row 2: Two-column body ────────────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=32, pady=(16, 0))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Left card — indicators
        left_card = card(body)
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left_card.grid_columnconfigure(0, weight=1)
        left_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            left_card, text="  📐  Technical Indicators",
            font=font(13, "bold"), text_color=ACCENT_LIGHT,
            anchor="w", height=40,
            fg_color=ACCENT_SUBTLE, corner_radius=0,
        ).grid(row=0, column=0, sticky="ew")

        self._ind_scroll = ctk.CTkScrollableFrame(
            left_card, fg_color="transparent",
            scrollbar_button_color=BORDER_DEFAULT,
            scrollbar_button_hover_color=ACCENT,
        )
        self._ind_scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        # Right card — AI text
        right_card = card(body)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right_card.grid_columnconfigure(0, weight=1)
        right_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            right_card, text="  🧠  Claude AI Analysis",
            font=font(13, "bold"), text_color=ACCENT_LIGHT,
            anchor="w", height=40,
            fg_color=ACCENT_SUBTLE, corner_radius=0,
        ).grid(row=0, column=0, sticky="ew")

        self._ai_box = ctk.CTkTextbox(
            right_card, font=MONO(), fg_color="#060D18",
            text_color="#A3E635", wrap="word", state="disabled",
        )
        self._ai_box.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        # ── Row 3: Bottom action bar ──────────────────────────────
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=3, column=0, sticky="ew", padx=32, pady=(12, 24))

        ghost_btn(nav, text="← Holdings",
                  command=lambda: self._app.show_panel("holdings")).pack(side="left")
        primary_btn(
            nav, text="✨  Use AI Suggestion →",
            command=self._go_suggest, width=220,
        ).pack(side="right")

        # Populate if cached data already exists
        self._current_stock = default
        if (self._state.ai_indicators.get("_data_available")
                and self._state.selected_stock == default):
            self._render_indicators(self._state.ai_indicators)
            if self._state.ai_analysis_text:
                self._set_ai_text(self._state.ai_analysis_text)
        else:
            self._set_ai_text("Click  'Analyze Stock'  to get AI insights.\n\n"
                               "Make sure you are connected to Breeze first.")
            self._render_indicators({})

    # ─────────────────────────────────────────────────────────────
    # Event handlers
    # ─────────────────────────────────────────────────────────────

    def _on_stock_change(self, value: str) -> None:
        self._current_stock = value
        self._status_l.configure(text="Ready — click Analyze.", text_color=TEXT_SECONDARY)
        self._set_ai_text("Click  'Analyze Stock'  to get AI insights.")
        self._render_indicators({})

    def _start_analysis(self) -> None:
        stock = self._stock_var.get()
        if "Fetch holdings" in stock or not stock:
            self._status_l.configure(text="⚠️  Fetch holdings first.", text_color=WARN)
            return
        if not self._state.is_connected:
            self._status_l.configure(text="⚠️  Not connected to Breeze.", text_color=WARN)
            return

        self._analyze_btn.configure(state="disabled", text="⏳  Fetching…")
        self._status_l.configure(text="Downloading OHLC data…", text_color=TEXT_SECONDARY)
        self._set_ai_text("Fetching data… please wait.")

        # Identify exchange for this stock from holdings
        exchange = "NSE"
        for h in self._state.holdings:
            if h.get("stock_code") == stock:
                exchange = h.get("exchange", "NSE")
                break

        def _bg() -> None:
            try:
                self.after(0, lambda: self._status_l.configure(
                    text="Computing indicators…", text_color=TEXT_SECONDARY
                ))
                df = market_data.fetch_historical_ohlc(
                    self._state.breeze_instance, stock, exchange, days=400
                )
                inds = market_data.compute_indicators(df)

                # Cache in state
                self._state.ai_indicators = inds
                self._state.selected_stock = stock
                self._state.selected_exchange = exchange

                self.after(0, self._render_indicators, inds)
                self.after(0, lambda: self._status_l.configure(
                    text="Calling Claude AI…", text_color=TEXT_SECONDARY
                ))

                try:
                    analysis = ai_engine.analyze_stock(
                        stock, inds,
                        self._state.active_client_name or "",
                        state=self._state,
                    )
                    self._state.ai_analysis_text = analysis
                    self.after(0, self._set_ai_text, analysis)
                    self.after(0, lambda: self._status_l.configure(
                        text=f"✅  Analysis complete for {stock}.", text_color=SUCCESS
                    ))
                except ai_engine.AIEngineError as ai_err:
                    self.after(0, self._set_ai_text,
                               f"AI unavailable: {ai_err}\n\n"
                               "Indicators above are still usable.")
                    self.after(0, lambda: self._status_l.configure(
                        text="⚠️  AI call failed — indicators still available.",
                        text_color=WARN,
                    ))

            except Exception as exc:
                log.error("Analysis pipeline error: %s", exc, exc_info=True)
                self.after(0, lambda e=exc: self._status_l.configure(
                    text=f"🔴  Error: {e}", text_color=DANGER
                ))
                self.after(0, self._set_ai_text, f"Error: {exc}")
            finally:
                self.after(0, lambda: self._analyze_btn.configure(
                    state="normal", text="🧠  Analyze Stock"
                ))

        threading.Thread(target=_bg, daemon=True).start()

    def _go_suggest(self) -> None:
        if self._current_stock and "Fetch" not in self._current_stock:
            self._state.selected_stock = self._current_stock
        self._app.show_panel("suggest")

    # ─────────────────────────────────────────────────────────────
    # Rendering helpers
    # ─────────────────────────────────────────────────────────────

    def _set_ai_text(self, text: str) -> None:
        self._ai_box.configure(state="normal")
        self._ai_box.delete("1.0", "end")
        self._ai_box.insert("end", text)
        self._ai_box.configure(state="disabled")

    def _render_indicators(self, inds: dict) -> None:
        for w in self._ind_scroll.winfo_children():
            w.destroy()

        if not inds or not inds.get("_data_available"):
            ctk.CTkLabel(
                self._ind_scroll,
                text="No data yet. Click 'Analyze Stock'.",
                font=font(12), text_color=TEXT_SECONDARY,
            ).pack(pady=40)
            return

        cp = inds.get("Current_price", 0.0)

        groups = [
            ("💰  Price Context", [
                ("Current Price",      f"₹{inds.get('Current_price', 0):.2f}",     ACCENT_LIGHT),
                ("52W High",           f"₹{inds.get('High_52w', 0):.2f}",           TEXT_PRIMARY),
                ("52W Low",            f"₹{inds.get('Low_52w', 0):.2f}",            TEXT_PRIMARY),
                ("% Below 52W High",   f"-{inds.get('Price_from_52w_high', 0):.2f}%", DANGER),
                ("% Above 52W Low",    f"+{inds.get('Price_from_52w_low', 0):.2f}%",  SUCCESS),
                ("Support",            f"₹{inds.get('Support_level', 0):.2f}",      SUCCESS),
                ("Resistance",         f"₹{inds.get('Resistance_level', 0):.2f}",   WARN),
            ]),
            ("📈  Momentum", [
                ("RSI (14)",   self._rsi_str(inds),                         self._rsi_color(inds)),
                ("MACD Line",  f"{inds.get('MACD_line', 0):.4f}",           TEXT_PRIMARY),
                ("MACD Signal",f"{inds.get('MACD_signal', 0):.4f}",         TEXT_PRIMARY),
                ("MACD Hist",  f"{inds.get('MACD_hist', 0):.4f}",
                    SUCCESS if inds.get("MACD_hist", 0) >= 0 else DANGER),
            ]),
            ("📉  Trend", [
                ("EMA 20",  f"₹{inds.get('EMA_20', 0):.2f}",  SUCCESS if cp >= inds.get("EMA_20", 0) else DANGER),
                ("EMA 50",  f"₹{inds.get('EMA_50', 0):.2f}",  SUCCESS if cp >= inds.get("EMA_50", 0) else DANGER),
                ("SMA 200", f"₹{inds.get('SMA_200', 0):.2f}" if inds.get("SMA_200") else "N/A (< 200 days)",
                    SUCCESS if cp >= inds.get("SMA_200", 0) > 0 else TEXT_SECONDARY),
            ]),
            ("🌡️  Volatility", [
                ("ATR (14)",   f"₹{inds.get('ATR_14', 0):.2f}",      TEXT_PRIMARY),
                ("BB Upper",   f"₹{inds.get('BB_upper', 0):.2f}",     DANGER),
                ("BB Middle",  f"₹{inds.get('BB_middle', 0):.2f}",    TEXT_SECONDARY),
                ("BB Lower",   f"₹{inds.get('BB_lower', 0):.2f}",     SUCCESS),
                ("BB Width",   f"{inds.get('BB_width', 0):.2f}%",     TEXT_PRIMARY),
            ]),
            ("📦  Volume", [
                ("Vol SMA 20",   f"{inds.get('Volume_SMA_20', 0):,.0f}",  TEXT_PRIMARY),
                ("Vol Ratio",    f"{inds.get('Volume_ratio', 1):.2f}x",
                    SUCCESS if inds.get("Volume_ratio", 1) >= 1.2
                    else DANGER if inds.get("Volume_ratio", 1) < 0.8
                    else TEXT_SECONDARY),
            ]),
        ]

        for group_label, rows in groups:
            # Group header
            gh = ctk.CTkFrame(self._ind_scroll, fg_color=ACCENT_SUBTLE, corner_radius=6)
            gh.pack(fill="x", pady=(10, 2), padx=4)
            ctk.CTkLabel(gh, text=group_label, font=font(11, "bold"),
                         text_color=ACCENT_LIGHT, anchor="w").pack(padx=12, pady=6)

            # Rows
            for i, (label_txt, val_txt, val_color) in enumerate(rows):
                bg = BG_ROW_A if i % 2 == 0 else BG_ROW_B
                row = ctk.CTkFrame(self._ind_scroll, fg_color=bg, corner_radius=4)
                row.pack(fill="x", padx=4, pady=1)
                row.grid_columnconfigure(1, weight=1)
                ctk.CTkLabel(row, text=label_txt, font=font(11), text_color=TEXT_SECONDARY,
                             anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=6)
                ctk.CTkLabel(row, text=val_txt, font=font(11, "bold"), text_color=val_color,
                             anchor="e").grid(row=0, column=1, sticky="e", padx=10, pady=6)

    # ─────────────────────────────────────────────────────────────
    # RSI helpers
    # ─────────────────────────────────────────────────────────────

    def _rsi_str(self, inds: dict) -> str:
        v = inds.get("RSI_14", 50.0)
        tag = "Overbought" if v > 70 else "Oversold" if v < 30 else "Neutral"
        return f"{v:.1f}  ({tag})"

    def _rsi_color(self, inds: dict) -> str:
        v = inds.get("RSI_14", 50.0)
        if v > 70:
            return DANGER
        if v < 40:
            return SUCCESS
        return WARN
