"""
ui/dashboard_panel.py
=====================
Visual analytics dashboard using matplotlib embedded in CustomTkinter.
"""
from __future__ import annotations
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ui.theme import *

class DashboardPanel(ctk.CTkFrame):
    def __init__(self, master, app, state) -> None:
        super().__init__(master, fg_color=BG_BASE, corner_radius=0)
        self._app = app
        self._state = state
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew", padx=32, pady=(28, 0))
        ctk.CTkLabel(
            hdr, text="Analytics Dashboard", font=font(22, "bold"),
            text_color=TEXT_BRIGHT
        ).pack(side="left")

        # Container for Charts
        left_card = card(self)
        left_card.grid(row=1, column=0, sticky="nsew", padx=(32, 16), pady=20)
        
        right_card = card(self)
        right_card.grid(row=1, column=1, sticky="nsew", padx=(16, 32), pady=20)

        # Build charts
        self._build_portfolio_chart(left_card)
        self._build_execution_chart(right_card)

    def _build_portfolio_chart(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            parent, text="Portfolio Allocation (Quantity)", font=font(14, "bold"), text_color=TEXT_BRIGHT
        ).pack(pady=(16, 8))

        holdings = self._state.holdings
        if not holdings:
            ctk.CTkLabel(parent, text="No holdings data available.", text_color=TEXT_MUTED).pack(expand=True)
            return

        labels = [h["stock_code"] for h in holdings if h["quantity"] > 0]
        sizes = [h["quantity"] for h in holdings if h["quantity"] > 0]

        if not sizes:
            ctk.CTkLabel(parent, text="No positive quantity holdings.", text_color=TEXT_MUTED).pack(expand=True)
            return

        fig, ax = plt.subplots(figsize=(5, 4), facecolor=BG_SURFACE)
        ax.set_facecolor(BG_SURFACE)
        
        # Dark theme adjustments
        plt.rcParams['text.color'] = TEXT_BRIGHT
        plt.rcParams['axes.labelcolor'] = TEXT_SECONDARY
        plt.rcParams['xtick.color'] = TEXT_SECONDARY
        plt.rcParams['ytick.color'] = TEXT_SECONDARY
        
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, 
               colors=[ACCENT, SUCCESS, WARN, DANGER, "#8A2BE2", "#00CED1", "#FF8C00"])
        ax.axis('equal') 

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def _build_execution_chart(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            parent, text="Algorithm Success Rate (Mock)", font=font(14, "bold"), text_color=TEXT_BRIGHT
        ).pack(pady=(16, 8))
        
        fig, ax = plt.subplots(figsize=(5, 4), facecolor=BG_SURFACE)
        ax.set_facecolor(BG_SURFACE)
        
        algorithms = ['Linear', 'Pyramid', 'Martingale']
        success_rates = [85, 92, 78]
        
        ax.bar(algorithms, success_rates, color=[ACCENT, SUCCESS, WARN])
        ax.set_ylabel('Success %')
        ax.set_ylim(0, 100)
        
        # Dark theme adjustments
        ax.spines['bottom'].set_color(BORDER_SUBTLE)
        ax.spines['top'].set_color('none') 
        ax.spines['right'].set_color('none')
        ax.spines['left'].set_color(BORDER_SUBTLE)
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
