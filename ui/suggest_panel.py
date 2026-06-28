"""
ui/suggest_panel.py
===================
AI-powered GTT configuration suggester.

Three paths for the user to arrive at a configuration:
  1. Natural language → Claude extracts parameters.
  2. One of three strategy cards (AI / Conservative / Aggressive).
  3. Manual editing of the pre-filled form fields.

All Claude calls run in daemon threads.  The user must explicitly
click "Preview Orders →" before anything is written to state.planned_orders.
"""

from __future__ import annotations

import threading
import customtkinter as ctk
from typing import Any

from core import market_data, ai_engine
from core.gtt_engine import calculate_orders
from utils.logger import get_logger
from ui.theme import *

log = get_logger(__name__)


class SuggestPanel(ctk.CTkFrame):

    def __init__(self, master: Any, app: Any, state: Any) -> None:
        super().__init__(master, fg_color=BG_BASE, corner_radius=0)
        self._app   = app
        self._state = state
        self._build_ui()

    # ─────────────────────────────────────────────────────────────
    # Layout construction
    # ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        inds = self._state.ai_indicators
        stock = self._state.selected_stock or "?"
        cp    = inds.get("Current_price", 0.0) if inds else 0.0
        atr   = inds.get("ATR_14", 0.0)        if inds else 0.0
        res   = inds.get("Resistance_level", cp * 1.05) if inds else cp * 1.05
        fq    = self._state.selected_free_qty or 0

        # Pre-compute three strategy variants
        ai_sug  = self._state.ai_suggestion  # may be empty dict
        if not ai_sug and inds.get("_data_available"):
            ai_sug = market_data.suggest_gtt_parameters(inds, fq, cp)
            self._state.ai_suggestion = ai_sug

        cons_sug  = self._make_conservative(cp, atr, fq)
        aggr_sug  = self._make_aggressive(cp, atr, res, fq)

        # ── Row 0: Header ─────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 0))
        ctk.CTkLabel(hdr, text="AI GTT Suggester", font=font(22, "bold"),
                     text_color=TEXT_BRIGHT).pack(side="left")
        ctk.CTkLabel(hdr, text=f"  {stock}  ·  ₹{cp:.2f}  ·  {fq} free shares",
                     font=font(11), text_color=TEXT_SECONDARY).pack(side="left", pady=(6, 0))

        # ── Row 1: Natural language input ─────────────────────────
        nl_card = card(self)
        nl_card.grid(row=1, column=0, sticky="ew", padx=32, pady=(16, 0))
        nl_card.grid_columnconfigure(0, weight=1)

        nl_inner = ctk.CTkFrame(nl_card, fg_color="transparent")
        nl_inner.pack(fill="x", padx=20, pady=16)
        nl_inner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(nl_inner, text="Describe your exit strategy in plain English",
                     font=font(12, "bold"), text_color=TEXT_PRIMARY, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 6))

        self._nl_box = ctk.CTkTextbox(
            nl_inner, height=72, font=font(12),
            fg_color=BG_INPUT, text_color=TEXT_BRIGHT,
            border_color=BORDER_DEFAULT, border_width=1,
        )
        self._nl_box.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self._nl_box.insert("end",
            f"e.g. Sell my {stock} in 10 batches starting at "
            f"₹{cp * 1.03:.0f} going up by {max(1, round(atr * 0.5)):g} rupees each")

        nl_btns = ctk.CTkFrame(nl_inner, fg_color="transparent")
        nl_btns.grid(row=2, column=0, sticky="ew")
        self._parse_btn = primary_btn(
            nl_btns, text="🤖  Parse with AI", command=self._parse_nl, width=180, height=38,
        )
        self._parse_btn.pack(side="left")
        # Model badge
        ctk.CTkLabel(
            nl_btns, text="⚡  Gemini 3.5 Flash · Fast",
            font=font(10), text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(10, 0))
        self._parse_status = ctk.CTkLabel(
            nl_btns, text="", font=font(11), text_color=ACCENT_LIGHT,
        )
        self._parse_status.pack(side="left", padx=12)

        # ── Row 2: Three strategy cards ───────────────────────────
        cards_row = ctk.CTkFrame(self, fg_color="transparent")
        cards_row.grid(row=2, column=0, sticky="ew", padx=32, pady=(16, 0))
        cards_row.grid_columnconfigure(0, weight=1)
        cards_row.grid_columnconfigure(1, weight=1)
        cards_row.grid_columnconfigure(2, weight=1)

        self._build_strategy_card(
            cards_row, col=0,
            title="🤖  AI Suggestion",
            badge_color=ACCENT,
            sug=ai_sug,
            note=ai_sug.get("reasoning", "Run AI Analysis first.") if ai_sug else "Run AI Analysis first.",
            model_badge="Gemini 3.1 Pro",
        )
        self._build_strategy_card(
            cards_row, col=1,
            title="📐  Conservative",
            badge_color=INFO,
            sug=cons_sug,
            note="Smaller gap, more tiers. Lower risk profile.",
            model_badge="Gemini 3.1 Pro",
        )
        self._build_strategy_card(
            cards_row, col=2,
            title="🚀  Aggressive",
            badge_color=WARN,
            sug=aggr_sug,
            note="Targets resistance. Fewer, larger batches.",
            model_badge="Gemini 3.1 Pro",
        )

        # ── Row 3: Editable form ──────────────────────────────────
        form_card = card(self)
        form_card.grid(row=3, column=0, sticky="ew", padx=32, pady=(16, 0))

        strip = ctk.CTkFrame(form_card, fg_color=ACCENT_SUBTLE, corner_radius=0, height=40)
        strip.pack(fill="x")
        strip.pack_propagate(False)
        ctk.CTkLabel(strip, text="  ✏️  Fine-tune Parameters",
                     font=font(12, "bold"), text_color=ACCENT_LIGHT, anchor="w",
                     ).pack(fill="both", expand=True, padx=12)

        form_inner = ctk.CTkFrame(form_card, fg_color="transparent")
        form_inner.pack(fill="x", padx=24, pady=16)
        for i in range(5):
            form_inner.grid_columnconfigure(i * 2, weight=0)
            form_inner.grid_columnconfigure(i * 2 + 1, weight=1)

        self._fields: dict[str, ctk.CTkEntry] = {}
        form_defs = [
            ("total_shares", "Total Shares",   str(fq),                            "int"),
            ("batch_size",   "Batch Size",      str(ai_sug.get("batch_size", 10) if ai_sug else 10), "int"),
            ("base_trigger", "Base Trigger ₹",  str(ai_sug.get("base_trigger", "") if ai_sug else ""), "float"),
            ("price_gap",    "Price Gap ₹",     str(ai_sug.get("price_gap", "") if ai_sug else ""),   "float"),
            ("limit_offset", "Limit Offset ₹",  "0.05",                            "float"),
        ]

        for col_i, (key, lbl, default, _) in enumerate(form_defs):
            ctk.CTkLabel(form_inner, text=lbl, font=font(11, "bold"),
                         text_color=TEXT_SECONDARY, anchor="w").grid(
                row=0, column=col_i * 2, sticky="w", padx=(0 if col_i == 0 else 16, 4))
            e = form_entry(form_inner, width=120, height=38)
            e.grid(row=1, column=col_i * 2, sticky="ew", padx=(0 if col_i == 0 else 16, 0), pady=(4, 0))
            if default:
                e.insert(0, default)
            self._fields[key] = e

        self._form_err = ctk.CTkLabel(form_inner, text="", font=font(10), text_color=DANGER)
        self._form_err.grid(row=2, column=0, columnspan=10, sticky="w", pady=(4, 0))

        # ── Row 4: AI explanation box ─────────────────────────────
        exp_card = card(self)
        exp_card.grid(row=4, column=0, sticky="ew", padx=32, pady=(12, 0))
        exp_card.grid_columnconfigure(0, weight=1)

        exp_inner = ctk.CTkFrame(exp_card, fg_color="transparent")
        exp_inner.pack(fill="x", padx=4, pady=4)
        exp_inner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(exp_inner, text="  💡  AI Explanation",
                     font=font(11, "bold"), text_color=ACCENT_LIGHT, anchor="w").grid(
            row=0, column=0, sticky="w", padx=12, pady=(8, 4))

        self._exp_box = ctk.CTkTextbox(
            exp_inner, height=110, font=font(11),
            fg_color=BG_ELEVATED, text_color=TEXT_PRIMARY,
            wrap="word", state="disabled",
            border_color=BORDER_SUBTLE, border_width=1,
        )
        self._exp_box.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self._set_exp("Click 'Use This' on a strategy card to load an AI explanation.")

        # ── Row 5: Navigation ─────────────────────────────────────
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=5, column=0, sticky="ew", padx=32, pady=(12, 24))
        ghost_btn(nav, text="← Back", command=lambda: self._app.show_panel("analysis")).pack(side="left")
        primary_btn(nav, text="Preview Orders →", command=self._preview, width=220).pack(side="right")

    def _build_strategy_card(self, parent, col: int, title: str,
                               badge_color: str, sug: dict, note: str,
                               model_badge: str = "") -> None:
        c = ctk.CTkFrame(parent, fg_color=BG_SURFACE, corner_radius=12,
                          border_width=1, border_color=BORDER_CARD)
        c.grid(row=0, column=col, sticky="nsew",
               padx=(0 if col == 0 else 8, 0 if col == 2 else 8),
               pady=0, ipadx=4)

        # Title strip
        strip = ctk.CTkFrame(c, fg_color=badge_color, corner_radius=0, height=36)
        strip.pack(fill="x")
        strip.pack_propagate(False)
        ctk.CTkLabel(strip, text=title, font=font(12, "bold"),
                     text_color=TEXT_BRIGHT, anchor="w").pack(side="left", padx=12, pady=6)
        # Model badge
        if model_badge:
            ctk.CTkLabel(
                strip, text=model_badge, font=font(9),
                text_color=TEXT_BRIGHT, anchor="e",
            ).pack(side="right", padx=8)

        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        if sug:
            rows = [
                ("Base Trigger", f"₹{sug.get('base_trigger', 0):.2f}", TEXT_BRIGHT),
                ("Price Gap",    f"₹{sug.get('price_gap', 0):.2f}",    TEXT_PRIMARY),
                ("Batch Size",   str(sug.get("batch_size", 0)),         TEXT_PRIMARY),
                ("# Batches",    str(sug.get("num_batches", 0)),        TEXT_PRIMARY),
                ("Range",        f"₹{sug.get('price_range_low', 0):.1f}"
                                 f" → ₹{sug.get('price_range_high', 0):.1f}", SUCCESS),
            ]
            for lbl_t, val_t, val_c in rows:
                r = ctk.CTkFrame(inner, fg_color="transparent")
                r.pack(fill="x", pady=2)
                ctk.CTkLabel(r, text=lbl_t, font=font(10), text_color=TEXT_SECONDARY,
                             anchor="w").pack(side="left")
                ctk.CTkLabel(r, text=val_t, font=font(11, "bold"), text_color=val_c,
                             anchor="e").pack(side="right")
        else:
            ctk.CTkLabel(inner, text="Run AI Analysis\nfirst to populate.",
                         font=font(11), text_color=TEXT_MUTED, justify="center").pack(pady=8)

        ctk.CTkLabel(c, text=note, font=font(9), text_color=TEXT_SECONDARY,
                     wraplength=200, justify="center").pack(padx=10, pady=(0, 6))

        btn = ctk.CTkButton(
            c, text="Use This", height=32, corner_radius=6,
            fg_color=ACCENT_SUBTLE, hover_color=ACCENT,
            text_color=ACCENT_LIGHT, font=font(11, "bold"),
            state="normal" if sug else "disabled",
            command=lambda s=sug: self._use_suggestion(s),
        )
        btn.pack(fill="x", padx=14, pady=(0, 12))

    # ─────────────────────────────────────────────────────────────
    # Strategy helpers (Conservative / Aggressive)
    # ─────────────────────────────────────────────────────────────

    def _make_conservative(self, cp: float, atr: float, fq: int) -> dict:
        if cp <= 0:
            return {}
        base  = round(cp * 1.05 * 2) / 2
        gap   = max(0.5, round(atr * 0.3, 1))
        batch = max(1, fq // 8) if fq > 0 else 10
        num   = max(1, (fq + batch - 1) // batch) if fq > 0 else 0
        return {
            "base_trigger"    : base,
            "price_gap"       : gap,
            "batch_size"      : batch,
            "num_batches"     : num,
            "price_range_low" : base,
            "price_range_high": round(base + (num - 1) * gap, 2),
            "reasoning"       : "Conservative: 5% above current, smaller batches.",
        }

    def _make_aggressive(self, cp: float, atr: float, res: float, fq: int) -> dict:
        if cp <= 0:
            return {}
        base  = round(max(res, cp * 1.04) * 2) / 2
        gap   = max(0.5, round(atr * 0.8, 1))
        batch = max(1, fq // 4) if fq > 0 else 25
        num   = max(1, (fq + batch - 1) // batch) if fq > 0 else 0
        return {
            "base_trigger"    : base,
            "price_gap"       : gap,
            "batch_size"      : batch,
            "num_batches"     : num,
            "price_range_low" : base,
            "price_range_high": round(base + (num - 1) * gap, 2),
            "reasoning"       : "Aggressive: targets resistance level, larger gaps.",
        }

    # ─────────────────────────────────────────────────────────────
    # UI actions
    # ─────────────────────────────────────────────────────────────

    def _use_suggestion(self, sug: dict) -> None:
        """Fill the form fields with a strategy suggestion."""
        fmap = {
            "total_shares": str(self._state.selected_free_qty or ""),
            "batch_size"  : str(sug.get("batch_size", "")),
            "base_trigger": str(sug.get("base_trigger", "")),
            "price_gap"   : str(sug.get("price_gap", "")),
            "limit_offset": "0.05",
        }
        for key, val in fmap.items():
            e = self._fields[key]
            e.delete(0, "end")
            e.insert(0, val)

        self._form_err.configure(text="")

        # Fetch AI explanation in background
        stock = self._state.selected_stock or "?"
        inds  = self._state.ai_indicators
        fq    = self._state.selected_free_qty or 0

        if inds.get("_data_available"):
            self._set_exp("⏳  Asking Claude for an explanation…")

            def _bg() -> None:
                try:
                    explanation = ai_engine.suggest_exit_strategy(
                        stock, inds, fq, sug, state=self._state,
                    )
                    self.after(0, self._set_exp, explanation)
                except ai_engine.AIEngineError as exc:
                    self.after(0, self._set_exp,
                               f"AI explanation unavailable: {exc}\n\n"
                               f"Strategy reasoning: {sug.get('reasoning', '')}")
            threading.Thread(target=_bg, daemon=True).start()
        else:
            self._set_exp(sug.get("reasoning", "No explanation available."))

    def _parse_nl(self) -> None:
        """Parse free-text from the NL box and fill the form."""
        text = self._nl_box.get("1.0", "end").strip()
        # Remove placeholder-looking text
        if text.startswith("e.g."):
            self._parse_status.configure(text="⚠️  Replace the placeholder with your own description.", text_color=WARN)
            return
        if not text:
            self._parse_status.configure(text="⚠️  Please enter your strategy.", text_color=WARN)
            return

        self._parse_btn.configure(state="disabled", text="⏳  Parsing…")
        self._parse_status.configure(text="Calling Claude…", text_color=TEXT_SECONDARY)
        stock = self._state.selected_stock or "?"
        cp    = self._state.ai_indicators.get("Current_price", 0.0)
        fq    = self._state.selected_free_qty or 0

        def _bg() -> None:
            try:
                result = ai_engine.parse_natural_language_strategy(
                    text, stock, cp, fq, state=self._state,
                )
                self.after(0, self._apply_nl_result, result)
            except ai_engine.AIEngineError as exc:
                self.after(0, lambda e=exc: self._parse_status.configure(
                    text=f"🔴  AI error: {e}", text_color=DANGER))
            finally:
                self.after(0, lambda: self._parse_btn.configure(
                    state="normal", text="🤖  Parse with AI"))
        threading.Thread(target=_bg, daemon=True).start()

    def _apply_nl_result(self, result: dict) -> None:
        mapping = {
            "total_shares": "total_shares",
            "batch_size"  : "batch_size",
            "base_trigger": "base_trigger",
            "price_gap"   : "price_gap",
            "limit_offset": "limit_offset",
        }
        filled = 0
        for key, field_key in mapping.items():
            val = result.get(key)
            if val is not None:
                e = self._fields[field_key]
                e.delete(0, "end")
                e.insert(0, str(val))
                filled += 1

        interp = result.get("interpretation", "")
        conf   = result.get("confidence", "low")
        conf_c = SUCCESS if conf == "high" else WARN if conf == "medium" else DANGER
        self._parse_status.configure(
            text=f"✅  {filled} field(s) filled | confidence: {conf} | {interp}",
            text_color=conf_c,
        )

    def _preview(self) -> None:
        """Validate fields → calculate orders → navigate to preview panel."""
        self._form_err.configure(text="")
        try:
            ts  = int(self._fields["total_shares"].get().strip())
            bs  = int(self._fields["batch_size"].get().strip())
            bt  = float(self._fields["base_trigger"].get().strip())
            pg  = float(self._fields["price_gap"].get().strip())
            lo  = float(self._fields["limit_offset"].get().strip())
        except ValueError as exc:
            self._form_err.configure(text=f"Invalid input: {exc}")
            return

        errors = []
        if ts <= 0:  errors.append("Total shares must be > 0")
        if bs <= 0:  errors.append("Batch size must be > 0")
        if bt <= 0:  errors.append("Base trigger must be > 0")
        if pg < 0:   errors.append("Price gap cannot be negative")
        if lo < 0:   errors.append("Limit offset cannot be negative")
        if errors:
            self._form_err.configure(text="  ·  ".join(errors))
            return

        stock    = self._state.selected_stock or ""
        exchange = self._state.selected_exchange or "NSE"

        try:
            orders = calculate_orders(stock, exchange, ts, bs, bt, pg, lo, "sell")
            self._state.planned_orders    = orders
            self._state.cfg_total_shares  = ts
            self._state.cfg_batch_size    = bs
            self._state.cfg_base_trigger  = bt
            self._state.cfg_price_gap     = pg
            self._state.cfg_limit_offset  = lo
            self._app.show_panel("preview")
        except Exception as exc:
            self._form_err.configure(text=str(exc))

    # ─────────────────────────────────────────────────────────────
    # AI explanation textbox helper
    # ─────────────────────────────────────────────────────────────

    def _set_exp(self, text: str) -> None:
        self._exp_box.configure(state="normal")
        self._exp_box.delete("1.0", "end")
        self._exp_box.insert("end", text)
        self._exp_box.configure(state="disabled")
