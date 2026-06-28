"""
ui/ai_settings_panel.py
========================
AI Model Configuration panel.

Allows the user to:
  - Configure Gemini API Key
  - View which Gemini model is assigned to each AI function
  - Override the model per-function (saved to database)
  - Estimate usage and view free tier limits
  - View model info cards for all tiers
  - Configure the NewsAPI key for sentiment features

Model overrides are persisted to the database app_config table
with keys like "ai_model_analyze_stock" = "smart".
"""

from __future__ import annotations

import threading
import webbrowser
import customtkinter as ctk
from typing import Any

from core import ai_engine
from core import news_fetcher
from core.database import get_config, set_config
from utils.logger import get_logger
from ui.theme import *

log = get_logger(__name__)

# ── Mapping between display names and tier keys ───────────────────
_MODEL_OPTIONS    = ["Gemini 3.5 Flash  (Fast)", "Gemini 3.1 Pro  (Smart)", "Gemini 3.1 Pro  (Best)"]
_DISPLAY_TO_TIER  = {
    "Gemini 3.5 Flash  (Fast)"  : "fast",
    "Gemini 3.1 Pro  (Smart)": "smart",
    "Gemini 3.1 Pro  (Best)"   : "best",
}
_TIER_TO_DISPLAY  = {v: k for k, v in _DISPLAY_TO_TIER.items()}

# ── AI functions shown in the assignment table ────────────────────
_FUNC_ROWS = [
    ("analyze_stock",  "Stock Analysis",          "smart", "Free"),
    ("suggest_exit",   "GTT Exit Suggestion",      "smart", "Free"),
    ("sentiment",      "News Sentiment",           "fast",  "Free"),
    ("portfolio",      "Portfolio Report",         "best",  "Free"),
    ("nlp_parse",      "Natural Language Parser",  "fast",  "Free"),
]


class AISettingsPanel(ctk.CTkFrame):

    def __init__(self, master: Any, app: Any, state: Any) -> None:
        super().__init__(master, fg_color=BG_BASE, corner_radius=0)
        self._app   = app
        self._state = state
        self._tier_vars: dict[str, ctk.StringVar] = {}
        self._load_preferences()
        self._build_ui()

    # ─────────────────────────────────────────────────────────────
    # Preference loading
    # ─────────────────────────────────────────────────────────────

    def _load_preferences(self) -> None:
        """Load saved model preferences from DB → AppState."""
        for func_name, _, default_tier, _ in _FUNC_ROWS:
            key   = f"ai_model_{func_name}"
            saved = get_config(key) or default_tier
            setattr(self._state, key, saved)
            log.debug("Loaded model pref: %s = %s", key, saved)

    # ─────────────────────────────────────────────────────────────
    # Layout construction
    # ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Scrollable content area ───────────────────────────────
        scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_BASE, corner_radius=0,
            scrollbar_button_color=BORDER_DEFAULT,
            scrollbar_button_hover_color=ACCENT,
        )
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # ── Row 0: Page header ────────────────────────────────────
        hdr = ctk.CTkFrame(scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=32, pady=(28, 0))
        ctk.CTkLabel(
            hdr, text="AI Model Configuration",
            font=font(22, "bold"), text_color=TEXT_BRIGHT,
        ).pack(side="left")
        ctk.CTkLabel(
            hdr, text="  Manage which Gemini model powers each feature",
            font=font(11), text_color=TEXT_SECONDARY,
        ).pack(side="left", pady=(6, 0))

        # ── Row 1: Gemini API connection status ───────────────────
        self._build_connection_card(scroll)

        # ── Row 2: Model assignment table ─────────────────────────
        self._build_assignment_table(scroll)

        # ── Row 3: Cost estimator ─────────────────────────────────
        self._build_cost_estimator(scroll)

        # ── Row 4: Model info cards ───────────────────────────────
        self._build_model_cards(scroll)

        # ── Row 5: NewsAPI configuration ──────────────────────────
        self._build_newsapi_section(scroll)

        # ── Spacer at bottom ──────────────────────────────────────
        ctk.CTkFrame(scroll, height=32, fg_color="transparent").pack()

    # ─────────────────────────────────────────────────────────────
    # Section builders
    # ─────────────────────────────────────────────────────────────

    def _build_connection_card(self, parent: ctk.CTkFrame) -> None:
        c = card(parent)
        c.pack(fill="x", padx=32, pady=(20, 0))

        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)
        inner.grid_columnconfigure(1, weight=1)

        # Left: title
        ctk.CTkLabel(
            inner, text="🔑  Google Gemini API Key",
            font=font(14, "bold"), text_color=TEXT_BRIGHT, anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        status_val = ai_engine.get_gemini_api_key_status()
        if status_val == "configured":
            status_txt = "✅ API Key Configured"
            status_color = SUCCESS
        elif status_val == "invalid":
            status_txt = "🔴 Invalid Key"
            status_color = DANGER
        else:
            status_txt = "⚠️ API Key Required"
            status_color = WARN

        self._conn_status = ctk.CTkLabel(
            inner, text=status_txt,
            font=font(12, "bold"), text_color=status_color, anchor="w",
        )
        self._conn_status.grid(row=1, column=0, sticky="w", pady=(0, 10))

        # Entry and buttons
        key_row = ctk.CTkFrame(inner, fg_color="transparent")
        key_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self._gemini_key_entry = form_entry(
            key_row,
            placeholder="Paste your Gemini API key here (AIza...)",
            width=400, height=38,
            show="●"
        )
        self._gemini_key_entry.pack(side="left", padx=(0, 10))

        self._save_gemini_btn = primary_btn(
            key_row, text="💾 Save Key",
            width=120, height=38,
            command=self._save_gemini_key,
        )
        self._save_gemini_btn.pack(side="left", padx=(0, 10))

        self._test_btn = ghost_btn(
            key_row, text="🔗 Test Connection",
            width=160, height=38,
            command=self._test_connection,
        )
        self._test_btn.pack(side="left")

        # Helper text
        lbl = ctk.CTkLabel(
            inner, text="Get your free API key at: aistudio.google.com",
            font=ctk.CTkFont(family="Segoe UI", size=11, underline=True), text_color=ACCENT_LIGHT, cursor="hand2", anchor="w"
        )
        lbl.grid(row=3, column=0, sticky="w")
        lbl.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/apikey"))

    def _build_assignment_table(self, parent: ctk.CTkFrame) -> None:
        c = card(parent)
        c.pack(fill="x", padx=32, pady=(16, 0))

        # Header strip
        strip = ctk.CTkFrame(c, fg_color=ACCENT_SUBTLE, corner_radius=0, height=40)
        strip.pack(fill="x")
        strip.pack_propagate(False)
        strip.grid_columnconfigure(0, weight=1)

        hdr_f = ctk.CTkFrame(strip, fg_color="transparent")
        hdr_f.pack(fill="x", padx=12, pady=0)
        hdr_f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr_f, text="  Feature", font=font(11, "bold"),
                     text_color=ACCENT_LIGHT, anchor="w", width=230).pack(side="left")
        ctk.CTkLabel(hdr_f, text="Assigned Model", font=font(11, "bold"),
                     text_color=ACCENT_LIGHT, anchor="w", width=230).pack(side="left")
        ctk.CTkLabel(hdr_f, text="Est. Cost/Call", font=font(11, "bold"),
                     text_color=ACCENT_LIGHT, anchor="e").pack(side="right", padx=16)

        # Data rows
        for i, (func_name, label_text, default_tier, est_cost) in enumerate(_FUNC_ROWS):
            bg = BG_ROW_A if i % 2 == 0 else BG_ROW_B
            row = ctk.CTkFrame(c, fg_color=bg, corner_radius=0)
            row.pack(fill="x")

            # Feature label
            ctk.CTkLabel(
                row, text=f"  {label_text}", font=font(12),
                text_color=TEXT_PRIMARY, anchor="w", width=230,
            ).pack(side="left", padx=(4, 0), pady=10)

            # Cost label (packed right first so it doesn't get pushed)
            ctk.CTkLabel(
                row, text=est_cost, font=MONO_SM(),
                text_color=TEXT_SECONDARY, anchor="e",
            ).pack(side="right", padx=20, pady=10)

            # Model dropdown
            saved_tier    = getattr(self._state, f"ai_model_{func_name}", default_tier)
            display_value = _TIER_TO_DISPLAY.get(saved_tier, _TIER_TO_DISPLAY["smart"])
            var           = ctk.StringVar(value=display_value)
            self._tier_vars[func_name] = var

            ctk.CTkOptionMenu(
                row, variable=var, values=_MODEL_OPTIONS,
                width=210, height=34,
                fg_color=BG_INPUT, button_color=ACCENT,
                button_hover_color=ACCENT_HOVER,
                text_color=TEXT_BRIGHT, font=font(11),
                command=lambda val, fn=func_name: self._on_model_change(fn, val),
            ).pack(side="left", padx=8, pady=10)

        # Save all button
        save_row = ctk.CTkFrame(c, fg_color="transparent")
        save_row.pack(fill="x", padx=16, pady=(8, 14))
        self._save_status = ctk.CTkLabel(
            save_row, text="", font=font(10), text_color=SUCCESS,
        )
        self._save_status.pack(side="left", padx=4)
        primary_btn(
            save_row, text="💾  Save All Changes",
            command=self._save_all, width=200, height=36,
        ).pack(side="right")

    def _build_cost_estimator(self, parent: ctk.CTkFrame) -> None:
        c = card(parent)
        c.pack(fill="x", padx=32, pady=(16, 0))

        strip = ctk.CTkFrame(c, fg_color=ACCENT_SUBTLE, corner_radius=0, height=36)
        strip.pack(fill="x")
        strip.pack_propagate(False)
        ctk.CTkLabel(strip, text="  📊  Usage Estimator",
                     font=font(12, "bold"), text_color=ACCENT_LIGHT, anchor="w",
                     ).pack(fill="both", expand=True, padx=12)

        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)

        # Input fields row
        fields_f = ctk.CTkFrame(inner, fg_color="transparent")
        fields_f.pack(fill="x")

        self._est_stock  = self.__est_field(fields_f, "Stock analyses / day", "5")
        self._est_gtt    = self.__est_field(fields_f, "GTT suggestions / day", "3")
        self._est_senti  = self.__est_field(fields_f, "Sentiment checks / day", "10")

        # Button row
        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(fill="x", pady=(12, 0))
        primary_btn(btn_row, text="📊  Calculate", command=self._calculate_cost,
                    width=160, height=36).pack(side="left")

        # Result labels
        res_f = ctk.CTkFrame(btn_row, fg_color="transparent")
        res_f.pack(side="left", padx=24)
        self._est_daily   = self.__cost_label(res_f, "Daily API calls:")
        self._est_limit = self.__cost_label(res_f, "Free tier limit:")
        self._est_status  = self.__cost_label(res_f, "Status:")

    def __est_field(self, parent: ctk.CTkFrame, label: str, default: str) -> ctk.CTkEntry:
        """Helper: labelled entry for cost estimator."""
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=(0, 24))
        ctk.CTkLabel(f, text=label, font=font(10), text_color=TEXT_SECONDARY,
                     anchor="w").pack(anchor="w")
        e = form_entry(f, width=110, height=36)
        e.pack(anchor="w", pady=(4, 0))
        e.insert(0, default)
        return e

    def __cost_label(self, parent: ctk.CTkFrame, prefix: str) -> ctk.CTkLabel:
        """Helper: inline cost result label pair."""
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=(0, 20))
        ctk.CTkLabel(f, text=prefix, font=font(10), text_color=TEXT_SECONDARY).pack(anchor="w")
        lbl = ctk.CTkLabel(f, text="—", font=font(12, "bold"), text_color=ACCENT_LIGHT)
        lbl.pack(anchor="w")
        return lbl

    def _build_model_cards(self, parent: ctk.CTkFrame) -> None:
        row_f = ctk.CTkFrame(parent, fg_color="transparent")
        row_f.pack(fill="x", padx=32, pady=(16, 0))
        row_f.grid_columnconfigure(0, weight=1)
        row_f.grid_columnconfigure(1, weight=1)
        row_f.grid_columnconfigure(2, weight=1)

        # Card 1 — Gemini 3.5 Flash
        self._build_one_model_card(
            row_f, col=0,
            icon="⚡", title="Fast & Free",
            subtitle="Gemini 3.5 Flash",
            title_color=WARN,
            border_color=WARN_DIM,
            bg_color=WARN_BG,
            lines=[
                ("Cost",     "Free — 15 requests/minute"),
                ("Best for", "Sentiment, NLP parsing"),
                ("Limit",    "1,500 req/day free"),
                ("Badge",    ""),
            ],
            badge_text="",
        )
        # Card 2 — Gemini 3.1 Pro (highlighted)
        self._build_one_model_card(
            row_f, col=1,
            icon="✅", title="Recommended",
            subtitle="Gemini 3.1 Pro",
            title_color=SUCCESS,
            border_color=ACCENT,
            bg_color=ACCENT_SUBTLE,
            lines=[
                ("Cost",     "Free — 2 requests/minute"),
                ("Best for", "Stock analysis, GTT suggestions"),
                ("Limit",    "50 req/day free"),
                ("Badge",    "ACTIVE DEFAULT"),
            ],
            badge_text="ACTIVE DEFAULT",
        )
        # Card 3 — Gemini 3.1 Pro (Best)
        self._build_one_model_card(
            row_f, col=2,
            icon="🏆", title="Deep Analysis",
            subtitle="Gemini 3.1 Pro",
            title_color=ACCENT_LIGHT,
            border_color=ACCENT_LIGHT,
            bg_color=BG_SURFACE,
            lines=[
                ("Cost",     "Free — 2 requests/minute"),
                ("Best for", "Portfolio reports"),
                ("Note",     "Same model, used for complex tasks"),
                ("Badge",    ""),
            ],
            badge_text="",
        )

    def _build_one_model_card(
        self, parent: ctk.CTkFrame, col: int,
        icon: str, title: str, subtitle: str,
        title_color: str, border_color: str, bg_color: str,
        lines: list[tuple[str, str]], badge_text: str,
    ) -> None:
        c = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=12,
                          border_width=2, border_color=border_color)
        c.grid(row=0, column=col, sticky="nsew",
               padx=(0 if col == 0 else 8, 0 if col == 2 else 8), pady=0)

        # Title
        th = ctk.CTkFrame(c, fg_color="transparent")
        th.pack(fill="x", padx=16, pady=(14, 0))
        ctk.CTkLabel(th, text=f"{icon}  {title}", font=font(15, "bold"),
                     text_color=title_color, anchor="w").pack(side="left")
        if badge_text:
            ctk.CTkLabel(
                th, text=badge_text,
                font=font(8, "bold"), text_color=ACCENT,
                fg_color=ACCENT_SUBTLE, corner_radius=4,
            ).pack(side="right")
        ctk.CTkLabel(c, text=subtitle, font=font(11), text_color=TEXT_SECONDARY,
                     anchor="w").pack(fill="x", padx=16, pady=(2, 8))

        ctk.CTkFrame(c, height=1, fg_color=border_color).pack(fill="x", padx=16)

        for lbl, val in lines:
            if not val or lbl == "Badge":
                continue
            row = ctk.CTkFrame(c, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=3)
            ctk.CTkLabel(row, text=f"{lbl}:", font=font(10), text_color=TEXT_MUTED,
                         anchor="w", width=60).pack(side="left")
            ctk.CTkLabel(row, text=val, font=font(10, "bold"), text_color=TEXT_PRIMARY,
                         anchor="w", wraplength=160).pack(side="left")

        ctk.CTkFrame(c, height=14, fg_color="transparent").pack()  # bottom spacer

    def _build_newsapi_section(self, parent: ctk.CTkFrame) -> None:
        c = card(parent)
        c.pack(fill="x", padx=32, pady=(16, 0))

        strip = ctk.CTkFrame(c, fg_color=ACCENT_SUBTLE, corner_radius=0, height=36)
        strip.pack(fill="x")
        strip.pack_propagate(False)
        ctk.CTkLabel(strip, text="  📰  NewsAPI Key  (for Sentiment features)",
                     font=font(12, "bold"), text_color=ACCENT_LIGHT, anchor="w",
                     ).pack(fill="both", expand=True, padx=12)

        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=14)
        inner.grid_columnconfigure(1, weight=1)

        has_key = bool(news_fetcher.get_news_api_key())
        key_status_txt   = "✅  Configured" if has_key else "⚠️  Not configured"
        key_status_color = SUCCESS if has_key else WARN

        ctk.CTkLabel(inner, text="Status:", font=font(11), text_color=TEXT_SECONDARY,
                     anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._key_status_lbl = ctk.CTkLabel(
            inner, text=key_status_txt, font=font(11, "bold"),
            text_color=key_status_color, anchor="w",
        )
        self._key_status_lbl.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(inner, text="New key:", font=font(11), text_color=TEXT_SECONDARY,
                     anchor="w").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(10, 0))

        key_row = ctk.CTkFrame(inner, fg_color="transparent")
        key_row.grid(row=1, column=1, sticky="ew", pady=(10, 0))

        self._key_entry = form_entry(
            key_row,
            placeholder="Paste NewsAPI key from newsapi.org",
            width=380, height=36,
        )
        self._key_entry.pack(side="left")

        self._key_save_btn = ctk.CTkButton(
            key_row, text="💾  Save", width=90, height=36,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=TEXT_BRIGHT, font=font(11, "bold"), corner_radius=8,
            command=self._save_newsapi_key,
        )
        self._key_save_btn.pack(side="left", padx=(10, 0))

        self._key_msg = ctk.CTkLabel(key_row, text="", font=font(10), text_color=TEXT_SECONDARY)
        self._key_msg.pack(side="left", padx=10)

        ctk.CTkLabel(
            inner,
            text="Free tier: 100 requests/day · Paid tier: $449/month",
            font=font(9), text_color=TEXT_MUTED,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

    # ─────────────────────────────────────────────────────────────
    # Event handlers
    # ─────────────────────────────────────────────────────────────
    def _save_gemini_key(self) -> None:
        key = self._gemini_key_entry.get().strip()
        if not key:
            self._conn_status.configure(text="🔴 Key cannot be empty", text_color=DANGER)
            return
        try:
            ai_engine.store_gemini_api_key(key)
            self._conn_status.configure(text="✅ API Key Configured", text_color=SUCCESS)
            self._gemini_key_entry.delete(0, "end")
            self._gemini_key_entry.configure(placeholder_text="Key saved — enter new key to update")
        except Exception as exc:
            self._conn_status.configure(text=f"🔴 Save error: {exc}", text_color=DANGER)

    def _test_connection(self) -> None:
        """Test Gemini connection using AI engine helper."""
        self._test_btn.configure(state="disabled", text="⏳  Testing…")
        self._conn_status.configure(text="⏪  Connecting…", text_color=TEXT_SECONDARY)

        def _bg() -> None:
            success, msg = ai_engine.test_connection()
            if success:
                self.after(0, lambda: self._conn_status.configure(
                    text=f"🟢 {msg}", text_color=SUCCESS,
                ))
            else:
                self.after(0, lambda: self._conn_status.configure(
                    text=f"🔴 {msg[:80]}", text_color=DANGER,
                ))
            self.after(0, lambda: self._test_btn.configure(
                state="normal", text="🔗 Test Connection"
            ))

        threading.Thread(target=_bg, daemon=True).start()

    def _on_model_change(self, func_name: str, display_val: str) -> None:
        """Update in-memory preference immediately when dropdown changes."""
        tier = _DISPLAY_TO_TIER.get(display_val, "smart")
        setattr(self._state, f"ai_model_{func_name}", tier)
        self._save_status.configure(text="● Unsaved changes", text_color=WARN)

    def _save_all(self) -> None:
        """Persist all current dropdown selections to the database."""
        try:
            for func_name, *_ in _FUNC_ROWS:
                tier = getattr(self._state, f"ai_model_{func_name}", "smart")
                set_config(f"ai_model_{func_name}", tier)
            self._save_status.configure(
                text="✅  All preferences saved.", text_color=SUCCESS,
            )
            log.info("AI model preferences saved to database.")
        except Exception as exc:
            self._save_status.configure(
                text=f"🔴  Save error: {exc}", text_color=DANGER,
            )

    def _calculate_cost(self) -> None:
        """Compute usage estimate from entry fields."""
        try:
            n_stock = int(self._est_stock.get().strip() or "0")
            n_gtt   = int(self._est_gtt.get().strip()   or "0")
            n_senti = int(self._est_senti.get().strip()  or "0")
        except ValueError:
            self._est_daily.configure(text="Invalid input")
            return

        total_pro = n_stock + n_gtt

        self._est_daily.configure(text=str(total_pro + n_senti))
        self._est_limit.configure(text="50 req/day (3.1 Pro)")

        if total_pro > 50:
            self._est_status.configure(text="Approaching limit ⚠️", text_color=WARN)
        else:
            self._est_status.configure(text="Within free limits ✅", text_color=SUCCESS)

    def _save_newsapi_key(self) -> None:
        key = self._key_entry.get().strip()
        if not key:
            self._key_msg.configure(text="Key cannot be empty.", text_color=DANGER)
            return
        try:
            news_fetcher.store_news_api_key(key)
            self._key_msg.configure(text="✅  Saved!", text_color=SUCCESS)
            self._key_status_lbl.configure(text="✅  Configured", text_color=SUCCESS)
            self._key_entry.delete(0, "end")
            self._key_entry.configure(placeholder_text="Key saved — enter new key to update")
        except Exception as exc:
            self._key_msg.configure(text=f"Error: {exc}", text_color=DANGER)
