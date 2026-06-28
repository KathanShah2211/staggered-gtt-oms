"""
ui/preview_matrix.py  —  Premium order preview matrix.
"""
from __future__ import annotations
import customtkinter as ctk
from utils.logger import get_logger
from ui.theme import *

log = get_logger(__name__)


class PreviewMatrixPanel(ctk.CTkFrame):
    def __init__(self, master, app, state) -> None:
        super().__init__(master, fg_color=BG_BASE, corner_radius=0)
        self._app = app
        self._state = state
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 0))
        ctk.CTkLabel(hdr, text="Order Preview", font=font(22, "bold"), text_color=TEXT_BRIGHT).pack(side="left")
        ctk.CTkLabel(hdr, text=f"  Matrix for {self._state.selected_stock}", font=font(11), text_color=TEXT_SECONDARY).pack(side="left", pady=(6, 0))

        # ── Summary Bar ───────────────────────────────────────────
        orders = self._state.planned_orders
        tot_o = len(orders)
        tot_s = sum(o.quantity for o in orders)
        min_t = min((o.trigger_price for o in orders), default=0.0)
        max_t = max((o.trigger_price for o in orders), default=0.0)

        sum_bar = ctk.CTkFrame(self, fg_color=ACCENT_SUBTLE, corner_radius=8)
        sum_bar.grid(row=1, column=0, sticky="ew", padx=32, pady=(16, 0), ipady=4)
        
        txt = f"📦  {tot_o} orders   |   🪙  {tot_s} shares   |   💰  ₹{min_t:.2f} → ₹{max_t:.2f}"
        ctk.CTkLabel(sum_bar, text=txt, font=font(13, "bold"), text_color=ACCENT_LIGHT).pack(pady=8)

        # ── Table ─────────────────────────────────────────────────
        c = card(self)
        c.grid(row=2, column=0, sticky="nsew", padx=32, pady=(16, 16))
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(1, weight=1)

        th = ctk.CTkFrame(c, fg_color=BG_HEADER, corner_radius=0, height=44)
        th.grid(row=0, column=0, sticky="ew")
        th.grid_propagate(False)
        for t, w in [("Batch #", 80), ("Action", 90), ("Qty", 90), ("Trigger ₹", 160), ("Limit ₹", 160)]:
            ctk.CTkLabel(th, text=t, font=font(11, "bold"), text_color=TEXT_SECONDARY, width=w, anchor="w").pack(side="left", padx=16, pady=10)

        scroll = ctk.CTkScrollableFrame(c, fg_color="transparent", scrollbar_button_color=BORDER_DEFAULT, scrollbar_button_hover_color=ACCENT)
        scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        if not orders:
            ctk.CTkLabel(scroll, text="No orders computed. Go back to config.", font=font(13), text_color=TEXT_SECONDARY).pack(pady=40)
        else:
            for i, o in enumerate(orders):
                bg = BG_ROW_A if i % 2 == 0 else BG_ROW_B
                r = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=8)
                r.pack(fill="x", padx=4, pady=3)
                def _c(txt, w, clr=TEXT_BRIGHT):
                    ctk.CTkLabel(r, text=str(txt), font=font(13), text_color=clr, width=w, anchor="w").pack(side="left", padx=16, pady=10)
                
                _c(o.batch_number, 80, TEXT_SECONDARY)
                _c(o.action.upper(), 90, WARN)
                _c(o.quantity, 90)
                _c(f"₹{o.trigger_price:.2f}", 160, SUCCESS)
                _c(f"₹{o.limit_price:.2f}", 160, TEXT_SECONDARY)

        # ── Nav ───────────────────────────────────────────────────
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=3, column=0, sticky="ew", padx=32, pady=(0, 24))
        
        ghost_btn(nav, text="← Edit Config", command=lambda: self._app.show_panel("config")).pack(side="left")
        
        exe = primary_btn(nav, text=f"🚀  Place {tot_o} Orders →", command=lambda: self._app.show_panel("execute"), width=260)
        exe.pack(side="right")
        if not orders: exe.configure(state="disabled", fg_color=BORDER_DEFAULT)
