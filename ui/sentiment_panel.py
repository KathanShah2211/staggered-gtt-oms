"""
ui/sentiment_panel.py
=====================
News Sentiment & Market Mood panel.

Fetches live news headlines from NewsAPI, runs them through Claude
sentiment analysis, and presents a visual score + breakdown.

Requires:
  - NewsAPI key (configured in this panel, stored encrypted)
  - AWS Bedrock credentials (for Claude sentiment call)

All API calls are in daemon threads.
"""

from __future__ import annotations

import threading
import customtkinter as ctk
from typing import Any

from core import ai_engine
from core import news_fetcher
from utils.logger import get_logger
from ui.theme import *

log = get_logger(__name__)


class SentimentPanel(ctk.CTkFrame):

    def __init__(self, master: Any, app: Any, state: Any) -> None:
        super().__init__(master, fg_color=BG_BASE, corner_radius=0)
        self._app   = app
        self._state = state
        self._build_ui()

    # ─────────────────────────────────────────────────────────────
    # Layout
    # ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # ── Row 0: Header ─────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 0))
        ctk.CTkLabel(hdr, text="Market Sentiment & News", font=font(22, "bold"),
                     text_color=TEXT_BRIGHT).pack(side="left")

        # ── Row 1: NewsAPI key notice (conditional) ───────────────
        has_key = bool(news_fetcher.get_news_api_key())
        self._key_row = ctk.CTkFrame(self, fg_color="transparent")
        self._key_row.grid(row=1, column=0, sticky="ew", padx=32, pady=(12, 0))
        if not has_key:
            self._build_key_notice(self._key_row)

        # ── Row 2: Controls bar ───────────────────────────────────
        ctrl = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=10,
                             border_width=1, border_color=BORDER_CARD)
        ctrl.grid(row=2, column=0, sticky="ew", padx=32, pady=(12, 0))

        ctk.CTkLabel(ctrl, text="Stock", font=font(11, "bold"),
                     text_color=TEXT_SECONDARY).pack(side="left", padx=(16, 8), pady=14)

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
            width=200, height=36,
            fg_color=BG_INPUT, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            text_color=TEXT_BRIGHT, font=font(13),
        )
        self._dd.pack(side="left", padx=(0, 16), pady=14)

        self._status_l = ctk.CTkLabel(ctrl, text="", font=font(11),
                                       text_color=TEXT_SECONDARY)
        self._status_l.pack(side="left", fill="x", expand=True, padx=8)

        # Model badge — Gemini 3.5 Flash is used for sentiment
        ctk.CTkLabel(
            ctrl, text="🤖  Gemini 3.5 Flash · Free & Fast",
            font=font(10), text_color=TEXT_SECONDARY,
        ).pack(side="right", padx=(0, 8))

        self._all_btn = ghost_btn(ctrl, text="📊  All Holdings", command=self._analyze_all,
                                   width=150, height=36)
        self._all_btn.pack(side="right", padx=(8, 8), pady=14)

        self._go_btn = primary_btn(ctrl, text="📰  Fetch & Analyze", command=self._start,
                                    width=180, height=36)
        self._go_btn.pack(side="right", padx=(0, 16), pady=14)

        # Usage note beneath controls bar
        ctk.CTkLabel(
            self,
            text="Uses Gemini 3.5 Flash · Free tier  ·  "
                 "Configure models in AI Settings ⚙️",
            font=font(9), text_color=TEXT_MUTED, anchor="e",
        ).grid(row=2, column=0, sticky="e", padx=36, pady=(2, 0))

        # ── Row 3: Score card ─────────────────────────────────────
        self._score_card = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=14,
                                         border_width=1, border_color=BORDER_CARD)
        self._score_card.grid(row=3, column=0, sticky="ew", padx=32, pady=(16, 0))
        self._score_inner = ctk.CTkFrame(self._score_card, fg_color="transparent")
        self._score_inner.pack(pady=16)
        ctk.CTkLabel(self._score_inner, text="—", font=font(56, "bold"),
                     text_color=TEXT_MUTED).pack(side="left", padx=20)
        self._score_num  = self._score_inner.winfo_children()[0]
        self._score_info = ctk.CTkFrame(self._score_inner, fg_color="transparent")
        self._score_info.pack(side="left", padx=8)
        self._score_label = ctk.CTkLabel(self._score_info, text="Awaiting analysis",
                                          font=font(18, "bold"), text_color=TEXT_MUTED)
        self._score_label.pack(anchor="w")
        self._score_summ  = ctk.CTkLabel(self._score_info, text="",
                                          font=font(11), text_color=TEXT_SECONDARY,
                                          wraplength=680, justify="left")
        self._score_summ.pack(anchor="w", pady=(4, 0))

        # ── Row 4: Key positives / risks ──────────────────────────
        pr_row = ctk.CTkFrame(self, fg_color="transparent")
        pr_row.grid(row=4, column=0, sticky="ew", padx=32, pady=(12, 0))
        pr_row.grid_columnconfigure(0, weight=1)
        pr_row.grid_columnconfigure(1, weight=1)

        self._pos_card = self._build_posneg_card(pr_row, 0, "✅  Key Positives", SUCCESS_BG, SUCCESS)
        self._neg_card = self._build_posneg_card(pr_row, 1, "⚠️  Key Risks",     DANGER_BG, DANGER)

        # ── Row 5: Headlines list ─────────────────────────────────
        hl_card = card(self)
        hl_card.grid(row=5, column=0, sticky="nsew", padx=32, pady=(12, 0))
        hl_card.grid_columnconfigure(0, weight=1)
        hl_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(hl_card, text="  📋  Recent Headlines",
                     font=font(12, "bold"), text_color=ACCENT_LIGHT,
                     anchor="w", height=36, fg_color=ACCENT_SUBTLE, corner_radius=0,
                     ).grid(row=0, column=0, sticky="ew")

        self._hl_scroll = ctk.CTkScrollableFrame(
            hl_card, height=160, fg_color="transparent",
            scrollbar_button_color=BORDER_DEFAULT,
            scrollbar_button_hover_color=ACCENT,
        )
        self._hl_scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        ctk.CTkLabel(self._hl_scroll, text="No headlines yet.",
                     font=font(12), text_color=TEXT_SECONDARY).pack(pady=20)

        # ── Row 6: AI Recommendation ──────────────────────────────
        rec_card = card(self)
        rec_card.grid(row=6, column=0, sticky="ew", padx=32, pady=(12, 24))

        inner = ctk.CTkFrame(rec_card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(inner, text="💡  AI Recommendation",
                     font=font(11, "bold"), text_color=ACCENT_LIGHT, anchor="w").pack(anchor="w")
        self._rec_label = ctk.CTkLabel(
            inner, text="Run an analysis to get a recommendation.",
            font=font(12), text_color=TEXT_SECONDARY, anchor="w", wraplength=900,
        )
        self._rec_label.pack(anchor="w", pady=(6, 0))

    # ─────────────────────────────────────────────────────────────
    # NewsAPI key notice card
    # ─────────────────────────────────────────────────────────────

    def _build_key_notice(self, parent: ctk.CTkFrame) -> None:
        notice = ctk.CTkFrame(parent, fg_color=WARN_BG, corner_radius=10,
                               border_width=1, border_color=WARN_DIM)
        notice.pack(fill="x")

        inner = ctk.CTkFrame(notice, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)
        inner.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(inner, text="⚠️", font=font(20)).grid(row=0, column=0, rowspan=2, padx=(0, 12))
        ctk.CTkLabel(inner, text="NewsAPI key required for live news headlines.",
                     font=font(12, "bold"), text_color=WARN, anchor="w").grid(
            row=0, column=1, sticky="w")
        ctk.CTkLabel(inner,
                     text="Get a free key at newsapi.org (100 requests/day free). Enter it below.",
                     font=font(10), text_color=TEXT_SECONDARY, anchor="w").grid(
            row=1, column=1, sticky="w")

        key_row = ctk.CTkFrame(inner, fg_color="transparent")
        key_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        self._key_entry = form_entry(key_row, placeholder="Paste NewsAPI key here", width=380, height=36)
        self._key_entry.pack(side="left")
        self._save_key_btn = ctk.CTkButton(
            key_row, text="💾 Save Key", width=110, height=36,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=TEXT_BRIGHT, font=font(12, "bold"), corner_radius=8,
            command=self._save_key,
        )
        self._save_key_btn.pack(side="left", padx=(10, 0))
        self._key_msg = ctk.CTkLabel(key_row, text="", font=font(10), text_color=TEXT_SECONDARY)
        self._key_msg.pack(side="left", padx=10)

    def _save_key(self) -> None:
        key = self._key_entry.get().strip()
        if not key:
            self._key_msg.configure(text="Key cannot be empty.", text_color=DANGER)
            return
        try:
            news_fetcher.store_news_api_key(key)
            self._key_msg.configure(text="✅  Key saved successfully!", text_color=SUCCESS)
            self._key_entry.configure(state="disabled")
            self._save_key_btn.configure(state="disabled")
        except Exception as exc:
            self._key_msg.configure(text=f"Error: {exc}", text_color=DANGER)

    # ─────────────────────────────────────────────────────────────
    # Positives / risks card helper
    # ─────────────────────────────────────────────────────────────

    def _build_posneg_card(self, parent, col: int, title: str,
                            bg_color: str, text_color: str) -> ctk.CTkFrame:
        c = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=10,
                          border_width=1, border_color=text_color)
        c.grid(row=0, column=col, sticky="nsew",
               padx=(0 if col == 0 else 8, 0 if col == 1 else 8), pady=0)
        ctk.CTkLabel(c, text=f"  {title}",
                     font=font(11, "bold"), text_color=text_color, anchor="w").pack(
            fill="x", padx=4, pady=(8, 4))
        return c

    def _set_posneg(self, card_frame: ctk.CTkFrame, items: list[str],
                    bullet_color: str) -> None:
        for w in card_frame.winfo_children()[1:]:   # keep header label
            w.destroy()
        for item in items:
            ctk.CTkLabel(card_frame, text=f"  •  {item}",
                         font=font(11), text_color=TEXT_PRIMARY,
                         anchor="w", wraplength=350,
                         ).pack(fill="x", padx=8, pady=2)
        ctk.CTkFrame(card_frame, height=8, fg_color="transparent").pack()  # spacer

    # ─────────────────────────────────────────────────────────────
    # Analysis pipeline
    # ─────────────────────────────────────────────────────────────

    def _start(self) -> None:
        stock = self._stock_var.get()
        if "Fetch holdings" in stock:
            self._status_l.configure(text="⚠️  Fetch holdings first.", text_color=WARN)
            return

        self._go_btn.configure(state="disabled", text="⏳  Analyzing…")
        self._status_l.configure(text=f"Fetching news for {stock}…", text_color=TEXT_SECONDARY)

        def _bg() -> None:
            headlines = news_fetcher.fetch_headlines(stock)
            self._state.news_headlines = headlines
            self.after(0, self._render_headlines, headlines)

            if not headlines:
                self.after(0, lambda: self._status_l.configure(
                    text="No headlines found. Check your NewsAPI key or try another stock.",
                    text_color=WARN,
                ))
                self.after(0, lambda: self._go_btn.configure(
                    state="normal", text="📰  Fetch & Analyze"))
                return

            self.after(0, lambda: self._status_l.configure(
                text=f"{len(headlines)} headlines found. Calling Claude…",
                text_color=TEXT_SECONDARY,
            ))
            try:
                sentiment = ai_engine.analyze_sentiment(
                    stock, headlines, state=self._state,
                )
                self._state.ai_sentiment = sentiment
                self.after(0, self._render_sentiment, sentiment)
                self.after(0, lambda: self._status_l.configure(
                    text=f"✅  Sentiment analysis complete for {stock}.",
                    text_color=SUCCESS,
                ))
            except ai_engine.AIEngineError as exc:
                self.after(0, lambda e=exc: self._status_l.configure(
                    text=f"⚠️  AI error: {e}", text_color=WARN))
            finally:
                self.after(0, lambda: self._go_btn.configure(
                    state="normal", text="📰  Fetch & Analyze"))

        threading.Thread(target=_bg, daemon=True).start()

    def _analyze_all(self) -> None:
        """Run sentiment for every stock in holdings sequentially."""
        stocks = [h.get("stock_code", "") for h in self._state.holdings if h.get("stock_code")]
        if not stocks:
            self._status_l.configure(text="⚠️  No holdings loaded.", text_color=WARN)
            return

        self._all_btn.configure(state="disabled", text="⏳  Analyzing all…")
        self._status_l.configure(
            text=f"Batch analyzing {len(stocks)} stocks…", text_color=TEXT_SECONDARY)

        def _bg() -> None:
            for i, stock in enumerate(stocks, 1):
                self.after(0, lambda s=stock, n=i, t=len(stocks):
                           self._status_l.configure(
                               text=f"Analyzing {s} ({n}/{t})…",
                               text_color=TEXT_SECONDARY))
                try:
                    headlines = news_fetcher.fetch_headlines(stock)
                    if headlines:
                        ai_engine.analyze_sentiment(
                            stock, headlines, state=self._state,
                        )
                except Exception as exc:
                    log.warning("Batch sentiment failed for %s: %s", stock, exc)

            self.after(0, lambda: self._status_l.configure(
                text="✅  Batch analysis complete.", text_color=SUCCESS))
            self.after(0, lambda: self._all_btn.configure(
                state="normal", text="📊  All Holdings"))

        threading.Thread(target=_bg, daemon=True).start()

    # ─────────────────────────────────────────────────────────────
    # Render helpers
    # ─────────────────────────────────────────────────────────────

    def _render_sentiment(self, s: dict) -> None:
        score = int(s.get("score", 5))
        label = s.get("label", "Neutral")
        summ  = s.get("summary", "")
        poss  = s.get("key_positives", [])
        risks = s.get("key_risks", [])
        rec   = s.get("recommendation", "")

        if score <= 3:
            score_color = DANGER
        elif score <= 6:
            score_color = WARN
        else:
            score_color = SUCCESS

        self._score_num.configure(text=str(score), text_color=score_color)
        self._score_label.configure(text=label, text_color=score_color)
        self._score_summ.configure(text=summ)

        self._set_posneg(self._pos_card, poss, SUCCESS)
        self._set_posneg(self._neg_card, risks, DANGER)
        self._rec_label.configure(text=rec or "No recommendation.")

    def _render_headlines(self, headlines: list[str]) -> None:
        for w in self._hl_scroll.winfo_children():
            w.destroy()
        if not headlines:
            ctk.CTkLabel(self._hl_scroll, text="No headlines fetched.",
                         font=font(12), text_color=TEXT_SECONDARY).pack(pady=20)
            return
        for i, hl in enumerate(headlines):
            bg = BG_ROW_A if i % 2 == 0 else BG_ROW_B
            r = ctk.CTkFrame(self._hl_scroll, fg_color=bg, corner_radius=6)
            r.pack(fill="x", padx=4, pady=2)
            ctk.CTkLabel(r, text=f"  📰  {hl}", font=font(11),
                         text_color=TEXT_PRIMARY, anchor="w", wraplength=900,
                         ).pack(fill="x", padx=8, pady=8)
