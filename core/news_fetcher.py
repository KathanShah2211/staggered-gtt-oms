"""
core/news_fetcher.py
====================
News headline fetcher using the NewsAPI (newsapi.org).

Free tier: 100 requests/day.
The API key is stored encrypted in database.app_config under "news_api_key".
It is configured once by the user via the Sentiment panel UI.
"""

from __future__ import annotations

from utils.logger import get_logger

log = get_logger(__name__)

_NEWSAPI_URL   = "https://newsapi.org/v2/everything"
_MAX_HEADLINES = 10
_REQUEST_TO    = 10   # seconds


# ─────────────────────────────────────────────────────────────────
# Headline fetcher
# ─────────────────────────────────────────────────────────────────

def fetch_headlines(
    stock_code:   str,
    company_name: str = "",
    api_key:      str = "",
) -> list[str]:
    """
    Fetch recent English news headlines for a stock from NewsAPI.

    Parameters
    ----------
    stock_code   : NSE/BSE symbol (e.g. "RELIANCE").
    company_name : Optional full company name for richer search results.
    api_key      : NewsAPI key. Falls back to get_news_api_key() if empty.

    Returns
    -------
    List of headline strings (up to 10).
    Returns an empty list on any error — never raises.
    """
    if not api_key:
        api_key = get_news_api_key() or ""

    if not api_key:
        log.warning(
            "No NewsAPI key configured for %s. "
            "Configure it in the Sentiment panel.",
            stock_code,
        )
        return []

    try:
        import requests
    except ImportError:
        log.error("'requests' library not installed. Run: pip install requests")
        return []

    # Build a search query: "RELIANCE OR Reliance Industries NSE India stock"
    parts = [stock_code]
    if company_name and company_name != stock_code:
        parts.append(company_name)
    query = " OR ".join(parts[:2]) + " NSE India stock"

    params: dict = {
        "q"       : query,
        "apiKey"  : api_key,
        "language": "en",
        "sortBy"  : "publishedAt",
        "pageSize": _MAX_HEADLINES,
    }

    try:
        resp = requests.get(_NEWSAPI_URL, params=params, timeout=_REQUEST_TO)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok":
            log.warning(
                "NewsAPI returned non-ok status for %s: %s",
                stock_code, data.get("message", "unknown"),
            )
            return []

        articles  = data.get("articles") or []
        headlines = []
        for art in articles:
            title = (art.get("title") or "").strip()
            if title and title.lower() != "[removed]":
                headlines.append(title)

        log.info("Fetched %d headline(s) for %s.", len(headlines), stock_code)
        return headlines[:_MAX_HEADLINES]

    except Exception as exc:
        log.warning("fetch_headlines failed for %s: %s", stock_code, exc)
        return []


# ─────────────────────────────────────────────────────────────────
# Key storage (encrypted)
# ─────────────────────────────────────────────────────────────────

def store_news_api_key(api_key: str) -> None:
    """
    Encrypt and persist the NewsAPI key in the SQLite database.

    Parameters
    ----------
    api_key : Plain-text NewsAPI key from newsapi.org.
    """
    from core.database  import set_config
    from core.encryption import encrypt

    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty.")

    encrypted = encrypt(api_key.strip())
    set_config("news_api_key", encrypted)
    log.info("NewsAPI key saved (encrypted) to database.")


def get_news_api_key() -> str | None:
    """
    Retrieve and decrypt the stored NewsAPI key.

    Returns
    -------
    Plain-text NewsAPI key string, or None if not yet configured.
    """
    from core.database   import get_config
    from core.encryption import decrypt, is_initialized

    # Encryption must be unlocked (master password entered) before we can decrypt
    if not is_initialized():
        log.debug("Encryption not initialised — cannot retrieve NewsAPI key.")
        return None

    try:
        encrypted = get_config("news_api_key")
        if not encrypted:
            return None
        return decrypt(encrypted)
    except Exception as exc:
        log.warning("Failed to retrieve NewsAPI key: %s", exc)
        return None
