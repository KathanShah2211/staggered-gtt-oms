"""
ui/theme.py
===========
Centralised design token system for Staggered GTT OMS.

All UI files import colours, fonts and helpers from here.
This ensures a single source of truth for the visual identity.
"""

import customtkinter as ctk

# ─────────────────────────────────────────────────────────────────
# Global CTk setup  (run once on import)
# ─────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ─────────────────────────────────────────────────────────────────
# Colour Palette  — Deep Navy Professional Trading Theme
# ─────────────────────────────────────────────────────────────────

# Backgrounds (darkest → lightest)
BG_BASE      = "#070B14"   # Root window — near-black navy
BG_SIDEBAR   = "#060912"   # Sidebar — absolute darkest
BG_SURFACE   = "#0C1220"   # Cards / panels
BG_ELEVATED  = "#111827"   # Slightly elevated elements
BG_INPUT     = "#0F1829"   # Entry fields
BG_HEADER    = "#080D1C"   # Top header strip inside cards

# Table rows
BG_ROW_A     = "#0C1424"
BG_ROW_B     = "#0A1020"
BG_ROW_HOVER = "#132040"

# Borders
BORDER_SUBTLE  = "#182038"
BORDER_DEFAULT = "#1E2D52"
BORDER_FOCUS   = "#2E4A8A"
BORDER_CARD    = "#1A2845"

# Accent — Electric Blue
ACCENT        = "#3B82F6"
ACCENT_HOVER  = "#2563EB"
ACCENT_PRESS  = "#1D4ED8"
ACCENT_GLOW   = "#1E3A6E"   # Muted accent background
ACCENT_LIGHT  = "#60A5FA"   # For text on dark bg
ACCENT_SUBTLE = "#0F2044"   # Very dim accent bg

# Status colours
SUCCESS        = "#10B981"
SUCCESS_DIM    = "#065F46"
SUCCESS_BG     = "#061A12"
DANGER         = "#F87171"
DANGER_DIM     = "#991B1B"
DANGER_BG      = "#1A0808"
WARN           = "#FBBF24"
WARN_DIM       = "#92400E"
WARN_BG        = "#1A1000"
INFO           = "#818CF8"
INFO_BG        = "#0F1030"

# Text hierarchy
TEXT_BRIGHT    = "#F1F5F9"   # Primary — headings
TEXT_PRIMARY   = "#CBD5E1"   # Body text
TEXT_SECONDARY = "#64748B"   # Secondary / hints
TEXT_MUTED     = "#374151"   # Very dim (disabled)
TEXT_ACCENT    = ACCENT_LIGHT

# Sidebar nav
NAV_ACTIVE_BG     = "#0F2044"
NAV_ACTIVE_TEXT   = ACCENT_LIGHT
NAV_ACTIVE_BORDER = ACCENT
NAV_HOVER_BG      = "#111C38"
NAV_TEXT          = "#8B9BB4"

# ─────────────────────────────────────────────────────────────────
# Typography helpers
# ─────────────────────────────────────────────────────────────────

def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)

def font_mono(size: int = 12) -> ctk.CTkFont:
    return ctk.CTkFont(family="Consolas", size=size)

# Preset font shortcuts
H1   = lambda: font(24, "bold")
H2   = lambda: font(18, "bold")
H3   = lambda: font(15, "bold")
BODY = lambda: font(13)
BODY_BOLD = lambda: font(13, "bold")
CAPTION = lambda: font(11)
CAPTION_BOLD = lambda: font(11, "bold")
SMALL = lambda: font(10)
MONO  = lambda: font_mono(12)
MONO_SM = lambda: font_mono(11)

# ─────────────────────────────────────────────────────────────────
# Widget factory helpers
# ─────────────────────────────────────────────────────────────────

def card(parent, **kwargs) -> ctk.CTkFrame:
    """Standard card frame."""
    defaults = dict(fg_color=BG_SURFACE, corner_radius=14,
                    border_width=1, border_color=BORDER_CARD)
    defaults.update(kwargs)
    return ctk.CTkFrame(parent, **defaults)


def section_header(parent, text: str, subtitle: str = "") -> ctk.CTkFrame:
    """Page-level header with optional subtitle."""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(frame, text=text, font=H1(), text_color=TEXT_BRIGHT).pack(side="left")
    if subtitle:
        ctk.CTkLabel(
            frame, text=f"  {subtitle}",
            font=CAPTION(), text_color=TEXT_SECONDARY,
        ).pack(side="left", pady=(6, 0))
    return frame


def primary_btn(parent, text: str, command=None, width: int = 180,
                height: int = 44, **kwargs) -> ctk.CTkButton:
    defaults = dict(
        text=text, command=command, width=width, height=height,
        fg_color=ACCENT, hover_color=ACCENT_HOVER,
        text_color=TEXT_BRIGHT, font=BODY_BOLD(),
        corner_radius=10,
    )
    defaults.update(kwargs)
    return ctk.CTkButton(parent, **defaults)


def ghost_btn(parent, text: str, command=None, width: int = 160,
              height: int = 40, **kwargs) -> ctk.CTkButton:
    defaults = dict(
        text=text, command=command, width=width, height=height,
        fg_color="transparent", hover_color=NAV_HOVER_BG,
        border_width=1, border_color=BORDER_DEFAULT,
        text_color=TEXT_SECONDARY, font=BODY(),
        corner_radius=8,
    )
    defaults.update(kwargs)
    return ctk.CTkButton(parent, **defaults)


def danger_btn(parent, text: str, command=None, width: int = 120,
               height: int = 38, **kwargs) -> ctk.CTkButton:
    defaults = dict(
        text=text, command=command, width=width, height=height,
        fg_color=DANGER_BG, hover_color=DANGER_DIM,
        border_width=1, border_color=DANGER_DIM,
        text_color=DANGER, font=BODY_BOLD(),
        corner_radius=8,
    )
    defaults.update(kwargs)
    return ctk.CTkButton(parent, **defaults)


def form_entry(parent, placeholder: str = "", show: str = "",
               width: int = 400, height: int = 42, **kwargs) -> ctk.CTkEntry:
    defaults = dict(
        placeholder_text=placeholder, show=show,
        width=width, height=height,
        fg_color=BG_INPUT, border_color=BORDER_DEFAULT,
        text_color=TEXT_BRIGHT,
        placeholder_text_color=TEXT_SECONDARY,
        font=BODY(), border_width=1,
    )
    defaults.update(kwargs)
    return ctk.CTkEntry(parent, **defaults)


def status_pill(parent, text: str, color: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent, text=text, font=CAPTION_BOLD(),
        text_color=color, fg_color=BG_ELEVATED,
        corner_radius=20, padx=12, pady=4,
    )


def divider(parent, horizontal: bool = True) -> ctk.CTkFrame:
    if horizontal:
        return ctk.CTkFrame(parent, height=1, fg_color=BORDER_SUBTLE)
    return ctk.CTkFrame(parent, width=1, fg_color=BORDER_SUBTLE)


def label(parent, text: str, size: int = 13, weight: str = "normal",
          color: str = TEXT_PRIMARY, **kwargs) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent, text=text, font=font(size, weight),
        text_color=color, **kwargs,
    )
