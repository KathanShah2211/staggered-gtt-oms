"""
ui/app.py
=========
Main window controller — fully resizable, starts maximized.

Changes from v1
---------------
- Window starts in 'zoomed' (maximised) state on Windows.
- Fully resizable with minsize guard (980 × 640).
- Premium dark-navy sidebar with left-border active indicator.
- Top content header bar that updates with the current panel name.
- AppState dataclass unchanged — still the single source of truth.
"""

from __future__ import annotations

import importlib
import customtkinter as ctk
from dataclasses import dataclass, field
from typing import Any

from ui.theme import (
    BG_BASE, BG_SIDEBAR, BG_SURFACE, BG_ELEVATED, BORDER_SUBTLE, BORDER_CARD,
    ACCENT, ACCENT_LIGHT, ACCENT_GLOW, ACCENT_SUBTLE,
    NAV_ACTIVE_BG, NAV_ACTIVE_TEXT, NAV_ACTIVE_BORDER, NAV_HOVER_BG, NAV_TEXT,
    TEXT_BRIGHT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    SUCCESS, DANGER, WARN,
    H1, H2, H3, BODY, BODY_BOLD, CAPTION, CAPTION_BOLD, SMALL, font,
)


# ─────────────────────────────────────────────────────────────────
# AppState  — single source of truth, passed by reference
# ─────────────────────────────────────────────────────────────────

@dataclass
class AppState:
    active_client_name: str | None = None
    breeze_instance:    Any        = None
    is_connected:       bool       = False

    holdings: list[dict] = field(default_factory=list)

    selected_stock:    str | None = None
    selected_exchange: str        = "NSE"
    selected_free_qty: int        = 0

    planned_orders: list = field(default_factory=list)

    cfg_total_shares: int   = 0
    cfg_batch_size:   int   = 0
    cfg_base_trigger: float = 0.0
    cfg_price_gap:    float = 0.0
    cfg_limit_offset: float = 0.0

    # ── AI / ML state (cached to avoid re-fetching on panel switch) ──
    ai_indicators:    dict  = field(default_factory=dict)
    ai_analysis_text: str   = ""
    ai_suggestion:    dict  = field(default_factory=dict)
    ai_sentiment:     dict  = field(default_factory=dict)
    news_headlines:   list  = field(default_factory=list)

    # ── AI model preferences (overridable via AI Settings panel) ──
    ai_model_analyze_stock: str = "smart"
    ai_model_suggest_exit:  str = "smart"
    ai_model_sentiment:     str = "fast"
    ai_model_portfolio:     str = "best"
    ai_model_nlp_parse:     str = "fast"


# ─────────────────────────────────────────────────────────────────
# Navigation map
# ─────────────────────────────────────────────────────────────────

_NAV = [
    ("clients",  "👤",  "Clients",       "Manage API credentials"),
    ("session",  "🔑",  "Session",       "Connect to Breeze API"),
    ("holdings", "📊",  "Holdings",      "Live portfolio view"),
    ("config",   "⚙️",   "Configure GTT", "Set staggered parameters"),
    ("preview",  "👁️",   "Preview",       "Review order matrix"),
    ("execute",  "🚀",  "Execute",       "Place GTT orders"),
    ("logs",     "📋",  "Logs",          "Order history & export"),
    ("dashboard","📈",  "Dashboard",     "Visual Analytics"),
    # ── AI Features ──────────────────────────────────────────────
    ("analysis",   "🧠",  "AI Analysis",   "Smart stock insights"),
    ("suggest",    "✨",  "AI Suggest",    "AI-powered GTT config"),
    ("sentiment",  "📰",  "Sentiment",     "News & market mood"),
    ("ai_settings","⚙️",  "AI Settings",   "Model config & costs"),
]

_PANEL_MAP = {
    "clients":   "ui.client_manager.ClientManagerPanel",
    "session":   "ui.session_panel.SessionPanel",
    "holdings":  "ui.holdings_panel.HoldingsPanel",
    "config":    "ui.config_panel.ConfigPanel",
    "preview":   "ui.preview_matrix.PreviewMatrixPanel",
    "execute":   "ui.execution_panel.ExecutionPanel",
    "logs":      "ui.logs_panel.LogsPanel",
    "dashboard": "ui.dashboard_panel.DashboardPanel",
    # ── AI panels ─────────────────────────────────────────────────
    "analysis":   "ui.analysis_panel.AnalysisPanel",
    "suggest":    "ui.suggest_panel.SuggestPanel",
    "sentiment":  "ui.sentiment_panel.SentimentPanel",
    "ai_settings":"ui.ai_settings_panel.AISettingsPanel",
}


# ─────────────────────────────────────────────────────────────────
# Main application window
# ─────────────────────────────────────────────────────────────────

class App(ctk.CTk):

    TITLE   = "Staggered GTT OMS  ·  ICICI Direct"
    MIN_W   = 980
    MIN_H   = 640
    START_W = 1200
    START_H = 760

    def __init__(self) -> None:
        super().__init__()
        self.state_obj = AppState()
        self._current_key: str | None = None
        self._current_panel: ctk.CTkFrame | None = None
        self._nav_rows: dict[str, dict] = {}

        self._configure_window()
        self._build_login_view()

    # ── Window ────────────────────────────────────────────────────

    def _configure_window(self) -> None:
        self.title(self.TITLE)
        self.configure(fg_color=BG_BASE)
        self.minsize(self.MIN_W, self.MIN_H)

        # Centre at START_W × START_H, then maximise
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = (sw - self.START_W) // 2
        y = (sh - self.START_H) // 2
        self.geometry(f"{self.START_W}x{self.START_H}+{x}+{y}")

        # Start maximised on Windows
        try:
            self.state("zoomed")
        except Exception:
            pass  # Non-Windows fallback — just use START_W × START_H

    # ── Phase 1: Login ────────────────────────────────────────────

    def _build_login_view(self) -> None:
        from ui.login_screen import LoginScreen
        for w in self.winfo_children():
            w.destroy()
        f = LoginScreen(self, self.state_obj, on_success=self._build_main_shell)
        f.pack(fill="both", expand=True)

    # ── Phase 2: Main shell ───────────────────────────────────────

    def _build_main_shell(self) -> None:
        for w in self.winfo_children():
            w.destroy()

        outer = ctk.CTkFrame(self, fg_color=BG_BASE, corner_radius=0)
        outer.pack(fill="both", expand=True)
        outer.grid_columnconfigure(1, weight=1)
        outer.grid_rowconfigure(0, weight=1)

        # Sidebar
        self._sidebar = ctk.CTkFrame(
            outer, width=230, fg_color=BG_SIDEBAR, corner_radius=0,
        )
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_propagate(False)
        self._build_sidebar()

        # Right content shell
        right = ctk.CTkFrame(outer, fg_color=BG_BASE, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        # Top breadcrumb / header strip
        self._top_strip = ctk.CTkFrame(
            right, fg_color=BG_BASE, height=52, corner_radius=0,
        )
        self._top_strip.grid(row=0, column=0, sticky="ew")
        self._top_strip.grid_propagate(False)
        self._build_top_strip(self._top_strip)

        # Thin horizontal rule
        ctk.CTkFrame(right, height=1, fg_color=BORDER_SUBTLE, corner_radius=0
                     ).grid(row=0, column=0, sticky="sew")

        # Content area
        self._content_area = ctk.CTkFrame(right, fg_color=BG_BASE, corner_radius=0)
        self._content_area.grid(row=1, column=0, sticky="nsew")

        self.show_panel("holdings")

    # ── Sidebar ───────────────────────────────────────────────────

    def _build_sidebar(self) -> None:
        sb = self._sidebar

        # ── Logo ──────────────────────────────────────────────────
        logo = ctk.CTkFrame(sb, fg_color="transparent")
        logo.pack(fill="x", padx=18, pady=(24, 0))

        ctk.CTkLabel(
            logo, text="GTT OMS",
            font=font(22, "bold"), text_color=ACCENT_LIGHT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            logo, text="ICICI Direct  ·  Staggered Orders",
            font=font(9), text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(1, 0))

        # ── Divider ───────────────────────────────────────────────
        ctk.CTkFrame(sb, height=1, fg_color=BORDER_SUBTLE).pack(
            fill="x", padx=0, pady=(18, 12)
        )

        # ── Connection pill ───────────────────────────────────────
        self._conn_frame = ctk.CTkFrame(sb, fg_color=BG_ELEVATED, corner_radius=8)
        self._conn_frame.pack(fill="x", padx=14, pady=(0, 16))

        self._conn_dot = ctk.CTkLabel(
            self._conn_frame, text="⚫", font=font(10),
            text_color=TEXT_MUTED,
        )
        self._conn_dot.pack(side="left", padx=(12, 4), pady=8)

        self._conn_label = ctk.CTkLabel(
            self._conn_frame, text="Disconnected",
            font=font(11), text_color=TEXT_SECONDARY, anchor="w",
        )
        self._conn_label.pack(side="left", fill="x", expand=True, pady=8)

        # ── Section label ─────────────────────────────────────────
        ctk.CTkLabel(
            sb, text="NAVIGATION",
            font=font(9, "bold"), text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=20, pady=(0, 6))

        # ── Nav items ─────────────────────────────────────────────
        self._nav_rows = {}
        _AI_KEYS = {"analysis", "suggest", "sentiment", "ai_settings"}
        _divider_inserted = False
        for key, icon, label_text, hint in _NAV:
            # Insert 'AI FEATURES' section label before first AI panel
            if key in _AI_KEYS and not _divider_inserted:
                ctk.CTkFrame(sb, height=1, fg_color=BORDER_SUBTLE).pack(
                    fill="x", padx=0, pady=(8, 4)
                )
                ctk.CTkLabel(
                    sb, text="AI FEATURES",
                    font=font(9, "bold"), text_color=TEXT_MUTED,
                ).pack(anchor="w", padx=20, pady=(0, 4))
                _divider_inserted = True
            row_data = self._build_nav_item(sb, key, icon, label_text, hint)
            self._nav_rows[key] = row_data

        # ── Divider ───────────────────────────────────────────────
        ctk.CTkFrame(sb, height=1, fg_color=BORDER_SUBTLE).pack(
            fill="x", padx=0, pady=(12, 0)
        )

        # ── Version ───────────────────────────────────────────────
        ctk.CTkLabel(
            sb, text="v1.0.0  ·  2024",
            font=font(9), text_color=TEXT_MUTED,
        ).pack(side="bottom", pady=14)

    def _build_nav_item(self, parent, key: str, icon: str,
                         label_text: str, hint: str) -> dict:
        """Build one sidebar nav row. Returns refs for active-state toggling."""

        container = ctk.CTkFrame(parent, fg_color="transparent", height=46)
        container.pack(fill="x", pady=1)
        container.pack_propagate(False)

        # Left accent border (hidden by default)
        accent_bar = ctk.CTkFrame(container, width=3, fg_color="transparent",
                                   corner_radius=0)
        accent_bar.pack(side="left", fill="y")

        # Button fills the rest
        btn = ctk.CTkButton(
            container,
            text=f" {icon}  {label_text}",
            anchor="w",
            height=46,
            fg_color="transparent",
            hover_color=NAV_HOVER_BG,
            text_color=NAV_TEXT,
            font=font(13),
            corner_radius=0,
            command=lambda k=key: self.show_panel(k),
        )
        btn.pack(side="left", fill="both", expand=True)

        return {"container": container, "btn": btn, "accent": accent_bar}

    def _set_nav_active(self, key: str) -> None:
        for k, row in self._nav_rows.items():
            if k == key:
                row["accent"].configure(fg_color=ACCENT)
                row["btn"].configure(
                    fg_color=NAV_ACTIVE_BG, text_color=ACCENT_LIGHT,
                    hover_color=NAV_ACTIVE_BG,
                )
            else:
                row["accent"].configure(fg_color="transparent")
                row["btn"].configure(
                    fg_color="transparent", text_color=NAV_TEXT,
                    hover_color=NAV_HOVER_BG,
                )

    # ── Top strip ─────────────────────────────────────────────────

    def _build_top_strip(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)

        self._breadcrumb = ctk.CTkLabel(
            parent, text="Holdings",
            font=font(14, "bold"), text_color=TEXT_BRIGHT, anchor="w",
        )
        self._breadcrumb.grid(row=0, column=0, sticky="w", padx=24, pady=14)

        self._top_status = ctk.CTkLabel(
            parent, text="",
            font=font(11), text_color=TEXT_SECONDARY, anchor="e",
        )
        self._top_status.grid(row=0, column=1, sticky="e", padx=24, pady=14)

    # ── Panel navigation ──────────────────────────────────────────

    def show_panel(self, key: str) -> None:
        if key not in _PANEL_MAP:
            return

        self._current_key = key
        self._set_nav_active(key)

        # Update breadcrumb
        nav_info = {row[0]: (row[2], row[3]) for row in _NAV}
        name, hint = nav_info.get(key, (key.title(), ""))
        self._breadcrumb.configure(text=name)
        self._top_status.configure(text=hint)

        # Lazy-import panel class
        module_path, cls_name = _PANEL_MAP[key].rsplit(".", 1)
        mod = importlib.import_module(module_path)
        PanelClass = getattr(mod, cls_name)

        if self._current_panel is not None:
            self._current_panel.destroy()

        self._current_panel = PanelClass(
            self._content_area, app=self, state=self.state_obj,
        )
        self._current_panel.pack(fill="both", expand=True)

    # ── Connection status (called by session_panel) ───────────────

    def update_connection_status(self, connected: bool, name: str = "") -> None:
        if connected:
            self._conn_dot.configure(text="🟢", text_color=SUCCESS)
            self._conn_label.configure(
                text=name[:22] if name else "Connected",
                text_color=SUCCESS,
            )
        else:
            self._conn_dot.configure(text="⚫", text_color=TEXT_MUTED)
            self._conn_label.configure(text="Disconnected", text_color=TEXT_SECONDARY)
