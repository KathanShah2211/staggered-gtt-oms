"""
core/breeze_client.py
=====================
ICICI Direct Breeze Connect API wrapper.

Wraps the official breeze-connect SDK to:
  - Initialize a BreezeConnect session with an app key.
  - Generate an authenticated session via daily session token.
  - Fetch portfolio holdings and normalize them into a consistent dict format.
  - Provide a clean interface for GTT order placement (used by gtt_engine.py).

All network-related exceptions are caught here and re-raised as BreezeAPIError
so that UI layers only need to handle one exception type.
"""

from __future__ import annotations

import json
from typing import Any

try:
    from breeze_connect import BreezeConnect
except ImportError:
    # Allow the app to import without crashing if SDK isn't installed yet.
    # Actual usage will raise an ImportError at runtime — shown in UI.
    BreezeConnect = None  # type: ignore[assignment,misc]


# -----------------------------------------------------------------
# Custom exception
# -----------------------------------------------------------------

class BreezeAPIError(Exception):
    """Raised for all Breeze API communication errors."""


# -----------------------------------------------------------------
# Session management
# -----------------------------------------------------------------

def create_session(
    app_key: str,
    secret_key: str,
    session_token: str,
) -> "BreezeConnect":
    """
    Initialize a BreezeConnect object and authenticate with the daily session token.

    Parameters
    ----------
    app_key       : ICICI Direct API App Key (plain text, decrypted from DB).
    secret_key    : ICICI Direct API Secret Key (plain text, decrypted from DB).
    session_token : Daily session token from ICICI Direct Breeze portal.

    Returns
    -------
    An authenticated BreezeConnect instance ready for API calls.

    Raises
    ------
    BreezeAPIError on any connection or authentication failure.
    """
    if BreezeConnect is None:
        raise BreezeAPIError(
            "breeze-connect SDK is not installed. "
            "Run: pip install breeze-connect"
        )

    try:
        breeze = BreezeConnect(api_key=app_key)
        breeze.generate_session(secret_key=secret_key, api_session=session_token)
        return breeze
    except Exception as exc:
        raise BreezeAPIError(
            f"Failed to create Breeze session: {exc}"
        ) from exc


# -----------------------------------------------------------------
# Holdings fetcher
# -----------------------------------------------------------------

def fetch_holdings(breeze: "BreezeConnect") -> list[dict[str, Any]]:
    """
    Fetch demat portfolio holdings from the NSE exchange.

    Normalises each holding into:
        {
          "stock_code"  : str,
          "isin"        : str,
          "quantity"    : int,
          "free_qty"    : int,
          "exchange"    : str,   # "NSE"
        }

    Returns an empty list if holdings are empty or the API returns no data.

    Raises
    ------
    BreezeAPIError on API failure (non-200 response or network error).
    """
    try:
        response = breeze.get_portfolio_holdings(
            exchange_code="NSE",
            from_date="",
            to_date="",
            stock_code="",
            portfolio_type="",
        )
    except Exception as exc:
        raise BreezeAPIError(f"Holdings fetch failed: {exc}") from exc

    # Validate response structure
    if not isinstance(response, dict):
        raise BreezeAPIError(
            f"Unexpected response type from get_portfolio_holdings: {type(response)}"
        )

    status = response.get("Status")
    if status != 200:
        error_msg = response.get("Error") or response.get("Message") or str(response)
        raise BreezeAPIError(f"Holdings API returned status {status}: {error_msg}")

    success_data = response.get("Success")
    if not success_data:
        # Empty portfolio — not an error, return empty list.
        return []

    if not isinstance(success_data, list):
        raise BreezeAPIError(
            f"Expected list in 'Success' key, got {type(success_data)}"
        )

    holdings: list[dict[str, Any]] = []
    for item in success_data:
        if not isinstance(item, dict):
            continue

        # The Breeze API uses 'stock_code' and may use various field names
        # for quantity.  We probe for the most common alternatives.
        stock_code = (
            item.get("stock_code")
            or item.get("stockCode")
            or item.get("symbol")
            or "UNKNOWN"
        )

        isin = item.get("isin") or item.get("ISIN") or ""

        # Total quantity held
        quantity = _safe_int(
            item.get("quantity")
            or item.get("total_quantity")
            or item.get("totalQuantity")
            or 0
        )

        # Free (un-pledged, un-locked) quantity
        free_qty = _safe_int(
            item.get("free_quantity")
            or item.get("freeQuantity")
            or item.get("available_quantity")
            or item.get("availableQuantity")
            or quantity  # fall back to total if free qty not reported separately
        )

        exchange = item.get("exchange_code") or item.get("exchangeCode") or "NSE"

        holdings.append(
            {
                "stock_code": str(stock_code).strip(),
                "isin": str(isin).strip(),
                "quantity": quantity,
                "free_qty": free_qty,
                "exchange": str(exchange).strip(),
            }
        )

    return holdings


# -----------------------------------------------------------------
# GTT order placement — thin wrapper used by gtt_engine.py
# -----------------------------------------------------------------

def place_gtt_single_leg(
    breeze: "BreezeConnect",
    stock_code: str,
    exchange_code: str,
    trigger_price: float,
    limit_price: float,
    quantity: int,
    action: str = "sell",
) -> dict[str, Any]:
    """
    Place a single-leg GTT (Good Till Triggered) limit order for the cash segment.

    Uses breeze.gtt_single_leg_place_order() from the official SDK.

    For equity/cash segment:
      - product  = "cash"
      - right    = ""  (not required for equity)
      - strike_price = ""  (not required for equity)
      - expiry_date  = ""  (not required for equity)

    Returns
    -------
    The raw response dict from the SDK.

    Raises
    ------
    BreezeAPIError on network or unexpected errors.
    """
    try:
        response = breeze.gtt_single_leg_place_order(
            exchange_code=exchange_code,
            stock_code=stock_code,
            product="cash",
            action=action,
            order_type="limit",
            quantity=str(quantity),
            price=str(round(limit_price, 2)),
            trigger_price=str(round(trigger_price, 2)),
            expiry_date="",
            right="",
            strike_price="",
        )
        return response if isinstance(response, dict) else {"raw": response}
    except Exception as exc:
        raise BreezeAPIError(
            f"gtt_single_leg_place_order raised an exception: {exc}"
        ) from exc


# -----------------------------------------------------------------
# Helper
# -----------------------------------------------------------------

def _safe_int(value: Any) -> int:
    """Safely convert a value to int, defaulting to 0 on failure."""
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return 0
