"""
ui/session_panel.py  —  Premium session panel.
"""
from __future__ import annotations
import threading
import customtkinter as ctk
from core import database
from core.breeze_client import create_session, BreezeAPIError
from utils.logger import get_logger
from ui.theme import *

log = get_logger(__name__)


class SessionPanel(ctk.CTkFrame):
    def __init__(self, master, app, state) -> None:
        super().__init__(master, fg_color=BG_BASE, corner_radius=0)
        self._app = app
        self._state = state
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Header ────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 0))
        ctk.CTkLabel(hdr, text="Connect Session", font=font(22, "bold"),
                     text_color=TEXT_BRIGHT).pack(side="left")
        ctk.CTkLabel(hdr, text="  Provide the daily token to activate your API session",
                     font=font(11), text_color=TEXT_SECONDARY).pack(side="left", pady=(6, 0))

        # ── Body (Centred Card) ───────────────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=32, pady=20)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        c = card(body, width=540, height=480)
        c.grid(row=0, column=0)
        c.grid_propagate(False)

        # Card header strip
        strip = ctk.CTkFrame(c, fg_color=ACCENT_SUBTLE, corner_radius=0, height=48)
        strip.pack(fill="x")
        strip.pack_propagate(False)
        ctk.CTkLabel(strip, text="  🔗  Authentication required", font=font(13, "bold"),
                     text_color=ACCENT_LIGHT, anchor="w").pack(fill="both", expand=True, padx=16)

        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=40, pady=32)

        ctk.CTkLabel(inner, text="Select Account", font=font(11, "bold"),
                     text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=(0, 4))
        
        clients = [row["client_name"] for row in database.get_all_clients()] or ["— No clients configured —"]
        self._client_var = ctk.StringVar(value=clients[0])
        self._dd = ctk.CTkOptionMenu(
            inner, variable=self._client_var, values=clients, height=44,
            fg_color=BG_INPUT, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            text_color=TEXT_BRIGHT, font=font(13), corner_radius=8
        )
        self._dd.pack(fill="x", pady=(0, 24))

        lbl_frame = ctk.CTkFrame(inner, fg_color="transparent")
        lbl_frame.pack(fill="x", pady=(0, 4))
        
        ctk.CTkLabel(lbl_frame, text="Daily Session Token", font=font(11, "bold"),
                     text_color=TEXT_SECONDARY, anchor="w").pack(side="left")
                     
        self._auto_btn = ctk.CTkButton(
            lbl_frame, text="1-Click Login (Auto)", width=120, height=24,
            fg_color=ACCENT_SUBTLE, hover_color=ACCENT_GLOW,
            text_color=ACCENT_LIGHT, font=font(10, "bold"), corner_radius=6,
            command=self._auto_login
        )
        self._auto_btn.pack(side="right")
        
        self._token_e = form_entry(inner, placeholder="Paste your API session token here", show="●")
        self._token_e.pack(fill="x", pady=(0, 16))
        self._token_e.bind("<Return>", lambda _: self._connect())

        self._status_l = ctk.CTkLabel(inner, text="", font=font(12, "bold"))
        self._status_l.pack(fill="x", pady=(0, 8))

        self._conn_btn = primary_btn(inner, text="Connect to Breeze", command=self._connect, width=460)
        self._conn_btn.pack(fill="x", pady=(0, 16))

        ghost_btn(inner, text="Disconnect Session", command=self._disconnect, width=460).pack(fill="x")

        # Initial state update
        if self._state.is_connected:
            self._set_status(f"🟢  Connected: {self._state.active_client_name}", SUCCESS)

    def _set_status(self, msg: str, color: str) -> None:
        self._status_l.configure(text=msg, text_color=color)

    def _connect(self) -> None:
        client = self._client_var.get()
        token  = self._token_e.get().strip()
        if "No clients" in client:
            self._set_status("⚠️  Configure a client first.", WARN); return
        if not token:
            self._set_status("⚠️  Token is required.", WARN); return

        self._conn_btn.configure(state="disabled", text="Connecting...")
        self._token_e.configure(state="disabled")
        self._set_status("⏳  Authenticating with ICICI Direct...", TEXT_SECONDARY)

        def _bg() -> None:
            try:
                ak, sk = database.get_client_keys(client)
                breeze = create_session(ak, sk, token)
                self._state.breeze_instance = breeze
                self._state.active_client_name = client
                self._state.is_connected = True
                self.after(0, self._on_success, client)
            except Exception as e:
                self.after(0, self._on_fail, str(e))
        threading.Thread(target=_bg, daemon=True).start()

    def _on_success(self, client: str) -> None:
        self._set_status(f"🟢  Connected successfully as {client}", SUCCESS)
        self._conn_btn.configure(state="normal", text="Connect to Breeze")
        self._token_e.configure(state="normal")
        self._token_e.delete(0, "end")
        self._app.update_connection_status(True, client)

    def _on_fail(self, err: str) -> None:
        self._set_status(f"🔴  Failed: {err}", DANGER)
        self._conn_btn.configure(state="normal", text="Connect to Breeze")
        self._token_e.configure(state="normal")
        self._state.is_connected = False
        self._app.update_connection_status(False)

    def _disconnect(self) -> None:
        self._state.breeze_instance = None
        self._state.active_client_name = None
        self._state.is_connected = False
        self._state.holdings = []
        self._set_status("⚫  Disconnected.", TEXT_SECONDARY)
        self._app.update_connection_status(False)

    def _auto_login(self) -> None:
        client = self._client_var.get()
        if "No clients" in client:
            self._set_status("⚠️  Configure a client first.", WARN); return
            
        self._auto_btn.configure(state="disabled", text="Waiting...")
        self._set_status("⏳  Please login in the opened browser window...", TEXT_SECONDARY)
        
        def _bg() -> None:
            try:
                ak, sk = database.get_client_keys(client)
                if ak == "MOCK":
                    token = "MOCK_SESSION_TOKEN_123"
                else:
                    from core.auth_automation import fetch_session_token
                    token = fetch_session_token(ak)
                
                self.after(0, lambda: self._token_e.delete(0, 'end'))
                self.after(0, lambda: self._token_e.insert(0, token))
                self.after(0, self._connect)
                
            except Exception as e:
                self.after(0, self._on_fail, str(e))
            finally:
                self.after(0, lambda: self._auto_btn.configure(state="normal", text="1-Click Login (Auto)"))
                
        threading.Thread(target=_bg, daemon=True).start()
