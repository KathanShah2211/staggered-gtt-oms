# Staggered GTT OMS — ICICI Direct

> A production-ready, multi-account **Good Till Triggered (GTT) Order Management System** for ICICI Direct, built with Python 3.10+, CustomTkinter, and SQLite.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation — Run from Source](#1-installation--run-from-source)
4. [First Launch — Master Password Setup](#2-first-launch--master-password-setup)
5. [Getting Your ICICI Breeze API Keys](#3-getting-your-icici-breeze-api-keys)
6. [Getting the Daily Session Token](#4-getting-the-daily-session-token)
7. [IP Whitelisting on the ICICI API Portal](#5-ip-whitelisting-on-the-icici-api-portal)
8. [How to Use the Application](#6-how-to-use-the-application)
9. [Building the Windows EXE](#7-building-the-windows-exe)
10. [Security Notes](#8-security-notes)
11. [Folder Structure](#9-folder-structure)
12. [Troubleshooting](#10-troubleshooting)

---

## Overview

Staggered GTT OMS lets you:
- Manage multiple ICICI Direct accounts (encrypted API credentials).
- Fetch live demat holdings.
- Configure **staggered GTT orders** — split a large position across multiple
  price levels (tiers), each placed as a separate GTT order.
- Preview the full order matrix before executing.
- Execute all batches in a background thread with an abort button.
- View complete order history with CSV export.

---

## Features

| Feature | Detail |
|---|---|
| 🔐 Local Encryption | PBKDF2HMAC + Fernet AES-256 for API Keys |
| 🛡️ Zero Password Storage | Your ICICI password is NEVER stored. Login happens directly on ICICI's portal via a secure browser modal. |
| 👤 Multi-Account | Unlimited encrypted client profiles |
| 📊 Analytics Dashboard | Real-time portfolio pie charts & simulated success metrics |
| 🪄 AI Auto-Fill | Gemini AI calculates optimal risk-based parameters using ATR & Volatility |
| ⚙️ Dynamic Staggering | Linear, Pyramid, and Martingale scaling algorithms |
| 👁 Preview Matrix | Read-only order review before execution |
| 🚀 1-Click Login | Automated token extraction using Playwright (No more copy-pasting!) |
| 📁 Local Only | Zero cloud, zero data leaves your machine |

---

## 1. Installation — Run from Source

### Prerequisites
- Python **3.10** or later (download from [python.org](https://python.org))
- pip (bundled with Python)

### Steps

```powershell
# 1. Clone or download the project
cd C:\path\to\staggered_gtt_oms

# 2. (Recommended) Create a virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python main.py
```

> **Windows Defender note:** If SmartScreen blocks the app, right-click
> the `.exe` → Properties → Unblock, or run from source as above.

---

## 2. First Launch — Local App Security Setup

On the very first launch, the app shows a **"Set App Password"** screen:

1. Enter a strong password (minimum 6 characters).
2. Re-enter it to confirm.
3. Click **"Set Password & Unlock"**.

> 🛡️ **Highly Secure:** The password is **never stored**. Only a random cryptographic salt and an encrypted verification token are saved locally. This password is ONLY used to encrypt your ICICI API Keys on your local hard drive. 

> ⚠️ **Important:** If you forget your App Password, there is no recovery.
> You will need to delete `data/oms.db` and start fresh (losing saved client credentials).

On subsequent launches, enter your password in the Unlock screen.
After **5 consecutive wrong attempts**, the application closes automatically.

---

## 3. Getting Your ICICI Breeze API Keys

1. Log in to [https://api.icicidirect.com/apiuser/login](https://api.icicidirect.com/apiuser/login)
2. Navigate to **API Applications → Create New App**.
3. Fill in the application name and redirect URL (can be `http://localhost`).
4. After creation, you will see:
   - **App Key** (also called `API Key`)
   - **Secret Key**
5. Copy both values — you will need to paste them into the **Clients** panel.

---

## 4. Getting the Daily Session Token (1-Click Login)

ICICI Direct Breeze API requires a fresh session token every day. We have built a fully automated 1-Click Login system using **Playwright**.

### Steps to Connect:
1. Make sure you have Playwright installed: `pip install playwright` and `playwright install chromium`
2. Open the **Session** panel in the app.
3. Select your saved account and click **1-Click Login (Auto)**.
4. A secure Chromium browser window will open directly to the ICICI login page.
5. **Insert your ICICI credentials.** (We DO NOT store your ICICI password to maintain maximum security trust!).
6. Once you log in, the app automatically extracts the `apisession` token from the callback URL and connects your session seamlessly!

### Testing without an ICICI Account?
You can use the built-in **Mock Broker**. Simply go to the Clients panel, click **✨ Mock Account**, and then log in using that account. The app will bypass the browser and connect you to a simulated local broker for risk-free testing!
---

## 5. IP Whitelisting on the ICICI API Portal

ICICI Direct requires all API calls to originate from a **whitelisted static IP address**.
Requests from non-whitelisted IPs will be rejected with an authentication error.

### Step-by-Step Instructions

1. Open [https://api.icicidirect.com/apiuser/login](https://api.icicidirect.com/apiuser/login) and log in.
2. Click on your application name under **"API Applications"**.
3. Scroll down to the **"IP Whitelist"** section.
4. Click **"Add IP"**.
5. Enter your **static public IP address** (find it at [https://whatismyip.com](https://whatismyip.com)).
6. Click **"Save"**.
7. Changes take effect within a few minutes.

> ⚠️ If you do not have a static IP (most home broadband connections are dynamic),
> you will need to:
> - Use a VPN with a static IP exit node, or
> - Run this application from a cloud VM (e.g. AWS EC2 with an Elastic IP), or
> - Contact your ISP to assign a static IP.

---

## 6. How to Use the Application

### Workflow

```
Login → Clients → Session → Holdings → Configure GTT → Preview → Execute → Logs
```

### Detailed Steps

| Step | Panel | Action |
|------|-------|--------|
| 1 | **Login** | Enter master password to unlock |
| 2 | **Clients** | Add your ICICI Direct App Key + Secret Key |
| 3 | **Session** | Select client → paste daily session token → Connect |
| 4 | **Holdings** | Click "Fetch Holdings" → see your portfolio |
| 5 | **Configure GTT** | Click "⚙ Configure GTT" on any stock row |
| 6 | | Set Total Shares, Batch Size, Base Trigger, Price Gap, Limit Offset |
| 7 | **Preview** | Review the computed order matrix |
| 8 | **Execute** | Click "Start Execution" → watch the live log |
| 9 | **Logs** | Filter and review order history; export to CSV |

### Staggered GTT Math

Given inputs:
- **Total Shares**: 100
- **Batch Size**: 10
- **Base Trigger**: ₹500.00
- **Price Gap**: ₹2.00
- **Limit Offset**: ₹0.05

The engine generates 10 orders:

| Batch | Trigger ₹ | Limit ₹  | Qty |
|-------|-----------|---------|-----|
| 1     | 500.00    | 499.95  | 10  |
| 2     | 502.00    | 501.95  | 10  |
| 3     | 504.00    | 503.95  | 10  |
| ...   | ...       | ...     | ... |
| 10    | 518.00    | 517.95  | 10  |

If `total_shares % batch_size != 0`, a partial final batch is added automatically.

---

## 7. Building the Windows EXE

```powershell
# From the project root, with venv activated:
.\build.bat
```

The compiled executable will be at:
```
dist\StaggeredGTT_OMS.exe
```

> **Important:** The `data/` folder must exist alongside the `.exe` on first launch.
> The app creates it automatically when run from source, but for distribution,
> copy the `data/` folder (or at minimum `data/.gitkeep`) next to the `.exe`.

---

## 8. Security Notes

| Concern | How it's handled |
|---------|-----------------|
| API Keys storage | AES-256 (Fernet) encrypted with PBKDF2HMAC-derived key — never plaintext |
| Master Password | Never stored — only a random salt + encrypted verification token |
| Session Tokens | Kept in memory only (AppState) — never written to any file |
| Database | Local SQLite file at `data/oms.db` — stays on your machine |
| Network | No outbound calls except to ICICI Direct Breeze API |
| Key derivation | PBKDF2HMAC-SHA256, 390,000 iterations, 16-byte random salt |

---

## 9. Folder Structure

```
staggered_gtt_oms/
├── main.py                   # Application entry point
├── requirements.txt          # Python dependencies
├── build.bat                 # PyInstaller build script
├── README.md                 # This file
├── core/
│   ├── __init__.py
│   ├── database.py           # SQLite layer (parameterized queries)
│   ├── encryption.py         # PBKDF2 + Fernet AES-256
│   ├── breeze_client.py      # Breeze API wrapper
│   └── gtt_engine.py         # Staggered math + execution loop
├── ui/
│   ├── __init__.py
│   ├── app.py                # Main window + AppState + navigation
│   ├── login_screen.py       # Master password unlock
│   ├── client_manager.py     # Add / view / delete client profiles
│   ├── session_panel.py      # Daily session token + connect
│   ├── holdings_panel.py     # Live holdings grid
│   ├── config_panel.py       # Staggered order configuration
│   ├── preview_matrix.py     # Read-only order preview table
│   ├── execution_panel.py    # Live execution + log console
│   └── logs_panel.py         # Order history + CSV export
├── utils/
│   ├── __init__.py
│   └── logger.py             # Daily rotating log files
└── data/
    ├── oms.db                # Auto-created SQLite database
    └── logs/
        └── YYYY-MM-DD.log   # Daily rotating application logs
```

---

## 10. Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: breeze_connect` | Run `pip install breeze-connect` |
| `ModuleNotFoundError: customtkinter` | Run `pip install customtkinter` |
| "Connection failed: IP not whitelisted" | Add your IP on the ICICI API portal (see Section 5) |
| "Session token expired" | Generate a new token — they expire at midnight IST |
| Holdings returns empty | Ensure the account has demat holdings and NSE exchange is selected |
| App crashes on launch | Check `data/logs/YYYY-MM-DD.log` for the Python traceback |
| Wrong master password (locked out) | Delete `data/oms.db` to reset (you will lose saved clients) |
| EXE won't launch | Run `StaggeredGTT_OMS.exe` from a terminal to see error output |

---

*Staggered GTT OMS — Built for serious traders who demand precision and security.*
