"""
ui/execution_panel.py  —  Premium execution control room.
"""
from __future__ import annotations
import threading
import customtkinter as ctk
from core.gtt_engine import place_staggered_gtt
from core.database import log_order
from utils.logger import get_logger
from ui.theme import *

log = get_logger(__name__)


class ExecutionPanel(ctk.CTkFrame):
    def __init__(self, master, app, state) -> None:
        super().__init__(master, fg_color=BG_BASE, corner_radius=0)
        self._app = app
        self._state = state
        self._stop_ev = threading.Event()
        self._run = False
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 0))
        ctk.CTkLabel(hdr, text="Execution Console", font=font(22, "bold"), text_color=TEXT_BRIGHT).pack(side="left")

        stock = self._state.selected_stock or "N/A"
        tot = len(self._state.planned_orders)

        # ── Stat Bar ──────────────────────────────────────────────
        sb = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=12, border_width=1, border_color=BORDER_CARD)
        sb.grid(row=1, column=0, sticky="ew", padx=32, pady=(16, 0))
        
        self._stats = {}
        for k, v, l, c in [("total", str(tot), "Total Orders", TEXT_BRIGHT),
                           ("success", "0", "Success", SUCCESS),
                           ("failed", "0", "Failed", DANGER),
                           ("skipped", "0", "Skipped", WARN)]:
            col = ctk.CTkFrame(sb, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True, pady=16)
            ctk.CTkLabel(col, text=v, font=font(24, "bold"), text_color=c).pack()
            ctk.CTkLabel(col, text=l, font=font(11), text_color=TEXT_SECONDARY).pack()
            self._stats[k] = col.winfo_children()[0]

        # ── Terminal ──────────────────────────────────────────────
        c = ctk.CTkFrame(self, fg_color="transparent")
        c.grid(row=2, column=0, sticky="nsew", padx=32, pady=(16, 0))
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(0, weight=1)

        self._log = ctk.CTkTextbox(
            c, font=MONO(), fg_color="#05080F", text_color="#A3E635",
            wrap="word", state="disabled", corner_radius=12,
            border_width=1, border_color=BORDER_CARD
        )
        self._log.grid(row=0, column=0, sticky="nsew", pady=(0, 16))

        self._prog = ctk.CTkProgressBar(c, height=6, corner_radius=3, progress_color=ACCENT, fg_color=BG_ELEVATED)
        self._prog.set(0.0)
        self._prog.grid(row=1, column=0, sticky="ew", pady=(0, 20))

        # ── Nav ───────────────────────────────────────────────────
        nav = ctk.CTkFrame(c, fg_color="transparent")
        nav.grid(row=2, column=0, sticky="ew", pady=(0, 24))

        ghost_btn(nav, text="← Back", command=lambda: self._app.show_panel("preview")).pack(side="left")

        self._abort = danger_btn(nav, text="⛔ Abort", command=self._abort_cb, width=140)
        self._abort.pack(side="right", padx=(12, 0))
        self._abort.configure(state="disabled")

        self._start = primary_btn(nav, text="🚀  Start Execution", command=self._start_cb, width=220)
        self._start.pack(side="right")

        if not self._state.is_connected:
            self._out("⚠️ Not connected to Breeze.\n")
            self._start.configure(state="disabled")
        elif not tot:
            self._out("⚠️ No orders configured.\n")
            self._start.configure(state="disabled")
        else:
            self._out(f"Ready. Target: {stock}. Press Start.\n")

    def _start_cb(self) -> None:
        if self._run: return
        self._run = True
        self._stop_ev.clear()
        self._prog.set(0.0)
        for k in ["success", "failed", "skipped"]: self._set_stat(k, 0, SUCCESS if k=="success" else DANGER if k=="failed" else WARN)
        
        self._start.configure(state="disabled", text="Running...")
        self._abort.configure(state="normal")
        self._out("\n" + "━"*60 + "\n")

        def _bg():
            try:
                sm = place_staggered_gtt(
                    self._state.breeze_instance, self._state.planned_orders,
                    self._state.active_client_name or "?", self._stop_ev,
                    lambda m: self.after(0, self._out, m+"\n"),
                    lambda c, t: self.after(0, self._prog.set, c/t if t else 0),
                    log_order
                )
                self.after(0, self._done, sm)
            except Exception as e:
                self.after(0, self._out, f"\n❌ Fatal: {e}\n")
                self.after(0, self._done, None)
        threading.Thread(target=_bg, daemon=True).start()

    def _abort_cb(self) -> None:
        if self._run:
            self._stop_ev.set()
            self._abort.configure(state="disabled", text="Aborting...")
            self._out("\n⛔ Abort signaled...\n")

    def _done(self, sm) -> None:
        self._run = False
        self._start.configure(state="normal", text="🚀  Start Execution")
        self._abort.configure(state="disabled", text="⛔ Abort")
        self._prog.set(1.0)
        if sm:
            self._set_stat("success", sm.success, SUCCESS)
            self._set_stat("failed", sm.failed, DANGER)
            self._set_stat("skipped", sm.skipped, WARN)
            self._out(f"\n{'⛔ Aborted' if sm.aborted else '✅ Complete'}.\n")

    def _out(self, txt: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", txt)
        self._log.see("end")
        self._log.configure(state="disabled")

    def _set_stat(self, k: str, v: int, c: str) -> None:
        if k in self._stats: self._stats[k].configure(text=str(v), text_color=c)
