"""
main.py
=======
Staggered GTT OMS — Application Entry Point.

Startup sequence
----------------
1. Configure the daily rotating logger.
2. Initialise (or open) the SQLite database.
3. Create and run the CustomTkinter App window.
"""

import sys
import os

# ── Make sure the project root is on sys.path when running as a frozen .exe ──
if getattr(sys, "frozen", False):
    # PyInstaller sets this attribute; the bundle dir is in sys._MEIPASS
    bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    sys.path.insert(0, bundle_dir)

# ── Logging must be initialised before anything else ─────────────────────────
from utils.logger import setup_logging, get_logger

setup_logging()
log = get_logger("main")

# ── Database ─────────────────────────────────────────────────────────────────
from core.database import init_db

try:
    init_db()
    log.info("Database initialised successfully.")
except Exception as exc:
    log.critical("Failed to initialise database: %s", exc, exc_info=True)
    # Show a basic tkinter error box if CTk hasn't loaded yet
    import tkinter as _tk
    _tk.Tk().withdraw()
    from tkinter import messagebox as _mb
    _mb.showerror(
        "Database Error",
        f"Could not initialise the database:\n\n{exc}\n\n"
        "Please ensure the 'data/' directory is writable.",
    )
    sys.exit(1)

# ── Launch the application ───────────────────────────────────────────────────
from ui.app import App

if __name__ == "__main__":
    log.info("Starting Staggered GTT OMS...")
    try:
        app = App()
        app.mainloop()
    except KeyboardInterrupt:
        log.info("Application closed by keyboard interrupt.")
    except Exception as exc:
        log.critical("Unhandled exception in main loop: %s", exc, exc_info=True)
        raise
    finally:
        log.info("Application exited.")
