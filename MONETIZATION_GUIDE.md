# Staggered GTT OMS — Monetization & Distribution Guide

> Saved: 2026-05-21 | Status: For future review

---

## 🏗️ Part 1 — Package It Properly

### Step 1: Build the .exe
```powershell
pip install -r requirements.txt
.\build.bat
# Output: dist\StaggeredGTT_OMS.exe
```

### Step 2: Code Sign the .exe (Critical for Trust)
Without a code signature, Windows Defender SmartScreen will block it for every customer.

| Option | Cost | Where to Buy |
|---|---|---|
| **Sectigo OV Certificate** | ~$200/yr | sectigo.com |
| **DigiCert** | ~$500/yr | digicert.com |
| **SignPath.io** | Free (open source) / Paid | signpath.io |

```powershell
# After buying a certificate, sign the exe:
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a dist\StaggeredGTT_OMS.exe
```

### Step 3: Create an Installer (Optional but Professional)
Instead of shipping a raw `.exe`, wrap it in a proper installer:

- **Inno Setup** — https://jrsoftware.org/isinfo.php — Free, widely used
- **NSIS** — https://nsis.sourceforge.io/ — Free, very customizable
- **InstallForge** — https://installforge.net/ — Free, beginner-friendly

This gives customers a familiar `Setup.exe` with a license agreement screen.

---

## 💰 Part 2 — Licensing & Copy Protection

### Option A — License Key System (Recommended)
Add a license key check on startup that calls your server.

**Services that handle this:**

| Service | Price | Notes |
|---|---|---|
| **Cryptolens** | Free tier + $40/mo | Best for Python apps |
| **LicenseSpring** | $59/mo | Enterprise-grade |
| **Keygen.sh** | $29/mo | Developer-friendly API |
| **MyCommerce** | % of sales | Handles payments too |

### Option B — Hardware-Locked License (Strongest)
Lock the license to the buyer's machine fingerprint (CPU ID, MAC address).
Use **PyArmor** or **Cryptolens** machine locking.

### Option C — SaaS Model (No Piracy Risk)
Host a web version — customers log in via browser, nothing to pirate.
(More complex to build, but zero distribution headaches.)

---

## 🛒 Part 3 — Where to Sell It

### Option A — Your Own Website (Best Margins)

| Component | Free Option | Paid Option |
|---|---|---|
| Website | GitHub Pages, Carrd.co | Webflow, WordPress |
| Payments | **Razorpay** (India, 2% fee) | Stripe, PayPal |
| File delivery | Google Drive link | SendOwl, Payhip |
| License keys | Cryptolens free tier | Cryptolens paid |

> **Razorpay** is best for India — supports UPI, net banking, cards, no monthly fee.

### Option B — Digital Product Marketplaces

| Platform | Commission | Best For |
|---|---|---|
| **Gumroad** | 10% | Fastest to set up |
| **Payhip** | 5% | Good for software |
| **Lemon Squeezy** | 5% + $0.50 | Global payments, GST handled |
| **AppSumo** | 30–40% | Huge audience, lifetime deals |

### Option C — Direct Outreach (Highest Revenue)
Target ICICI Direct power users directly:
- Telegram trading groups
- Zerodha Varsity forums, TradingQnA
- Twitter/X finance community (#trading, #ICICI, #GTT)
- r/IndianStockMarket subreddit
- LinkedIn — retail traders and sub-brokers

---

## 💵 Part 4 — Pricing Strategy

### Pricing Models

| Model | How it works | Recommended Price |
|---|---|---|
| **One-time** | Pay once, use forever | ₹2,000 – ₹5,000 |
| **Annual subscription** | Renew yearly for updates | ₹999 – ₹1,999/yr |
| **Per-seat** | Each ICICI account = 1 seat | ₹500/account/month |
| **Lifetime deal** | One-time, early-bird price | ₹4,999 (limited slots) |

### Suggested Tiers
```
🥉 Starter   — ₹999/yr   — 1 account, basic features
🥈 Pro       — ₹2,499/yr — 5 accounts, priority support
🥇 Unlimited — ₹4,999/yr — Unlimited accounts + custom features
```

---

## 📋 Part 5 — Legal Requirements (India)

| Requirement | Action |
|---|---|
| **GST Registration** | Required if annual revenue > ₹20L |
| **Terms of Service** | Publish before selling (use termly.io to generate) |
| **Privacy Policy** | Required — state what data you collect (answer: nothing, it's local) |
| **SEBI Disclaimer** | Add: *"This software does not provide investment advice"* |
| **Business registration** | Proprietorship / LLP / Pvt Ltd |

> ⚠️ **Disclaimer to add to the app and website:**
> *"Staggered GTT OMS is a tool for order management only. It does not provide
> financial or investment advice. Trading in securities involves risk. The developer
> is not responsible for any trading losses."*

---

## 🚀 Part 6 — Fastest Path to First Sale

```
Week 1:  Build landing page on Carrd.co (free)
         Set up Gumroad (no monthly fee, 10% cut)
         Upload the signed .exe + README

Week 2:  Post in 5 trading Telegram groups
         Post on r/IndianStockMarket
         Create a 2-minute demo video (screen record)

Week 3:  First customers → collect feedback
         Iterate on pain points

Month 2: Set up your own domain + Razorpay
         Move off Gumroad to keep 100% revenue
```

---

## 🎯 Unique Selling Points (for Marketing)

- ✅ **100% local** — API keys never leave your PC
- ✅ **Multi-account** — manage all family/client ICICI accounts
- ✅ **Staggered GTT** — ICICI's web UI only allows one GTT at a time
- ✅ **One-click batch execution** — save hours of manual order entry
- ✅ **Encrypted storage** — bank-grade AES-256 security
- ✅ **Complete audit trail** — full CSV export of all orders placed

---

## 📌 TODOs Before Launch

- [ ] Add license key validation (Cryptolens or similar)
- [ ] Code sign the .exe with an OV certificate
- [ ] Create an Inno Setup installer
- [ ] Add SEBI disclaimer screen on first launch
- [ ] Build a landing page (Carrd.co)
- [ ] Record a 2-minute demo video
- [ ] Set up Gumroad or Razorpay
- [ ] Draft Terms of Service and Privacy Policy
- [ ] Register for GST (when revenue threshold approaches)

---

*Last updated: 2026-05-21*
