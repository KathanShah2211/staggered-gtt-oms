"""
core/market_data.py
===================
Historical OHLC data fetcher and technical indicator engine.

Fetches daily price data via ICICI Breeze API (get_historical_data_v2)
and computes a comprehensive set of technical indicators using the
'ta' library.  Results are designed to be cached in AppState.ai_indicators.

All functions are pure I/O or pure math — no UI dependencies.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from utils.logger import get_logger

log = get_logger(__name__)

# ── Try to import the 'ta' library ───────────────────────────────
try:
    from ta.trend     import EMAIndicator, SMAIndicator, MACD
    from ta.momentum  import RSIIndicator
    from ta.volatility import AverageTrueRange, BollingerBands
    _TA_AVAILABLE = True
except ImportError:
    _TA_AVAILABLE = False
    log.warning(
        "'ta' library not installed — indicator computation disabled. "
        "Run: pip install ta"
    )

# ── Safe empty result returned when data is insufficient ─────────
EMPTY_INDICATORS: dict = {
    "EMA_20": 0.0, "EMA_50": 0.0, "SMA_200": 0.0,
    "RSI_14": 50.0,
    "MACD_line": 0.0, "MACD_signal": 0.0, "MACD_hist": 0.0,
    "ATR_14": 0.0,
    "BB_upper": 0.0, "BB_middle": 0.0, "BB_lower": 0.0, "BB_width": 0.0,
    "Volume_SMA_20": 0.0, "Volume_ratio": 1.0,
    "Current_price": 0.0,
    "High_52w": 0.0, "Low_52w": 0.0,
    "Price_from_52w_high": 0.0, "Price_from_52w_low": 0.0,
    "Support_level": 0.0, "Resistance_level": 0.0,
    "_data_available": False,
}


# ─────────────────────────────────────────────────────────────────
# OHLC Fetcher
# ─────────────────────────────────────────────────────────────────

def fetch_historical_ohlc(
    breeze:     Any,
    stock_code: str,
    exchange:   str = "NSE",
    days:       int = 90,
) -> pd.DataFrame:
    """
    Fetch daily OHLC candlestick data from the ICICI Breeze API.

    Parameters
    ----------
    breeze     : Authenticated BreezeConnect instance.
    stock_code : NSE/BSE stock symbol (e.g. "RELIANCE").
    exchange   : Exchange code, "NSE" or "BSE".
    days       : Number of calendar days to look back (default 90).
                 Pass 400+ for 52-week indicator coverage.

    Returns
    -------
    pd.DataFrame with columns [date, open, high, low, close, volume],
    sorted ascending by date. Empty DataFrame on any error.
    """
    try:
        to_dt   = datetime.now()
        from_dt = to_dt - timedelta(days=days)

        # Breeze API date format: "YYYY-MM-DDT07:00:00.000Z"
        from_str = from_dt.strftime("%Y-%m-%dT07:00:00.000Z")
        to_str   = to_dt.strftime("%Y-%m-%dT07:00:00.000Z")

        log.info(
            "Fetching OHLC for %s (%s)  %s → %s",
            stock_code, exchange, from_str[:10], to_str[:10],
        )

        response = breeze.get_historical_data_v2(
            interval      = "1day",
            from_date     = from_str,
            to_date       = to_str,
            stock_code    = stock_code,
            exchange_code = exchange,
            product_type  = "cash",
            expiry_date   = "",
            right         = "",
            strike_price  = "",
        )

        if not isinstance(response, dict):
            log.warning(
                "Unexpected response type from get_historical_data_v2: %s",
                type(response),
            )
            return pd.DataFrame()

        status = response.get("Status")
        if status != 200:
            log.warning(
                "Historical data API returned status %s: %s",
                status,
                response.get("Error") or response.get("Message") or str(response),
            )
            return pd.DataFrame()

        raw_data = response.get("Success")
        if not raw_data or not isinstance(raw_data, list):
            log.info("No historical data returned for %s.", stock_code)
            return pd.DataFrame()

        records = []
        for item in raw_data:
            if not isinstance(item, dict):
                continue
            try:
                # The Breeze API uses 'datetime' for the candle timestamp
                date_val = item.get("datetime") or item.get("date") or ""
                records.append({
                    "date"  : pd.to_datetime(date_val),
                    "open"  : float(item.get("open",   0) or 0),
                    "high"  : float(item.get("high",   0) or 0),
                    "low"   : float(item.get("low",    0) or 0),
                    "close" : float(item.get("close",  0) or 0),
                    "volume": float(item.get("volume", 0) or 0),
                })
            except (ValueError, TypeError) as exc:
                log.debug("Skipping malformed record: %s — %s", item, exc)
                continue

        if not records:
            log.warning("All %d records were malformed for %s.", len(raw_data), stock_code)
            return pd.DataFrame()

        df = (
            pd.DataFrame(records)
            .sort_values("date")
            .reset_index(drop=True)
        )
        # Drop rows with zero close price (data errors)
        df = df[df["close"] > 0].reset_index(drop=True)

        log.info("OHLC fetch complete: %d trading days for %s.", len(df), stock_code)
        return df

    except Exception as exc:
        log.error(
            "fetch_historical_ohlc failed for %s: %s",
            stock_code, exc, exc_info=True,
        )
        return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────
# Indicator Engine
# ─────────────────────────────────────────────────────────────────

def compute_indicators(df: pd.DataFrame) -> dict:
    """
    Compute a comprehensive set of technical indicators from an OHLC DataFrame.

    Requires at least 20 rows for most indicators.
    Requires 200+ rows for SMA_200 (otherwise stored as 0.0).

    Parameters
    ----------
    df : DataFrame from fetch_historical_ohlc().

    Returns
    -------
    dict with all indicator values as floats, plus
    "_data_available": bool indicating whether calculation succeeded.
    """
    if df.empty or len(df) < 15:
        log.warning(
            "Insufficient OHLC rows for indicator computation: %d rows.", len(df)
        )
        result = EMPTY_INDICATORS.copy()
        result["_data_available"] = False
        return result

    if not _TA_AVAILABLE:
        log.error(
            "'ta' library unavailable — cannot compute indicators. "
            "Run: pip install ta"
        )
        result = EMPTY_INDICATORS.copy()
        result["_data_available"] = False
        return result

    try:
        close  = df["close"]
        high   = df["high"]
        low    = df["low"]
        volume = df["volume"]

        result: dict = {}

        # ── Trend ─────────────────────────────────────────────────
        result["EMA_20"]  = _last(EMAIndicator(close, window=20).ema_indicator())
        result["EMA_50"]  = _last(EMAIndicator(close, window=50).ema_indicator())
        result["SMA_200"] = (
            _last(SMAIndicator(close, window=200).sma_indicator())
            if len(df) >= 200 else 0.0
        )

        # ── Momentum ──────────────────────────────────────────────
        result["RSI_14"]     = _last(RSIIndicator(close, window=14).rsi())
        macd_obj             = MACD(close)
        result["MACD_line"]  = _last(macd_obj.macd())
        result["MACD_signal"]= _last(macd_obj.macd_signal())
        result["MACD_hist"]  = _last(macd_obj.macd_diff())

        # ── Volatility ────────────────────────────────────────────
        result["ATR_14"] = _last(
            AverageTrueRange(high, low, close, window=14).average_true_range()
        )
        bb = BollingerBands(close, window=20, window_dev=2)
        result["BB_upper"]  = _last(bb.bollinger_hband())
        result["BB_middle"] = _last(bb.bollinger_mavg())
        result["BB_lower"]  = _last(bb.bollinger_lband())
        bm = result["BB_middle"]
        result["BB_width"]  = (
            round((result["BB_upper"] - result["BB_lower"]) / bm * 100, 2)
            if bm > 0 else 0.0
        )

        # ── Volume ────────────────────────────────────────────────
        vol_sma = float(
            volume.rolling(window=20).mean().iloc[-1]
            if len(volume) >= 20
            else volume.mean()
        )
        cur_vol = float(volume.iloc[-1])
        result["Volume_SMA_20"] = round(vol_sma, 0)
        result["Volume_ratio"]  = round(cur_vol / vol_sma, 2) if vol_sma > 0 else 1.0

        # ── Price context ─────────────────────────────────────────
        cur_price = float(close.iloc[-1])
        result["Current_price"] = round(cur_price, 2)

        high_52w = float(high.max())
        low_52w  = float(low.min())
        result["High_52w"] = round(high_52w, 2)
        result["Low_52w"]  = round(low_52w,  2)

        result["Price_from_52w_high"] = (
            round((high_52w - cur_price) / high_52w * 100, 2)
            if high_52w > 0 else 0.0
        )
        result["Price_from_52w_low"] = (
            round((cur_price - low_52w) / low_52w * 100, 2)
            if low_52w > 0 else 0.0
        )

        # Support / Resistance = swing low / high over last 20 trading days
        recent = df.tail(20)
        result["Support_level"]    = round(float(recent["low"].min()),  2)
        result["Resistance_level"] = round(float(recent["high"].max()), 2)

        result["_data_available"] = True

        log.info(
            "Indicators OK — %s: Price=₹%.2f  RSI=%.1f  ATR=₹%.2f",
            df.index[-1] if not df.empty else "N/A",
            result["Current_price"], result["RSI_14"], result["ATR_14"],
        )
        return result

    except Exception as exc:
        log.error("compute_indicators crashed: %s", exc, exc_info=True)
        result = EMPTY_INDICATORS.copy()
        result["_data_available"] = False
        return result


# ─────────────────────────────────────────────────────────────────
# Math-based GTT parameter suggester (NO AI / NO API call)
# ─────────────────────────────────────────────────────────────────

def suggest_gtt_parameters(
    indicators:    dict,
    free_qty:      int,
    current_price: float,
) -> dict:
    """
    Pure-math GTT staggered-exit parameter suggester.

    Uses RSI, ATR, and resistance level from compute_indicators()
    to derive sensible batch / trigger / gap values.

    Parameters
    ----------
    indicators    : Output of compute_indicators().
    free_qty      : Number of free (sellable) shares held.
    current_price : Fallback price if not in indicators dict.

    Returns
    -------
    dict:
        base_trigger     : float  — first GTT trigger price (₹)
        price_gap        : float  — ₹ increment between tiers
        batch_size       : int    — shares per GTT order
        num_batches      : int    — total orders
        price_range_low  : float  — lowest trigger (= base_trigger)
        price_range_high : float  — highest trigger
        reasoning        : str    — one-line human explanation
    """
    cp  = indicators.get("Current_price") or current_price
    rsi = indicators.get("RSI_14", 50.0)
    atr = indicators.get("ATR_14", 0.0) or (cp * 0.01)
    res = indicators.get("Resistance_level", 0.0) or (cp * 1.05)

    if cp <= 0:
        cp = current_price if current_price > 0 else 100.0

    # ── Base trigger ───────────────────────────────────────────────
    if rsi > 70:
        raw_base    = cp * 1.02
        reason_part = f"RSI {rsi:.0f} (overbought) → trigger near current price"
    elif rsi < 40:
        raw_base    = res
        reason_part = f"RSI {rsi:.0f} (oversold) → target resistance ₹{res:.2f}"
    else:
        raw_base    = cp * 1.03
        reason_part = f"RSI {rsi:.0f} (neutral) → 3% above current price"

    # Round to nearest ₹0.50
    base_trigger = round(raw_base * 2) / 2

    # ── Price gap ──────────────────────────────────────────────────
    raw_gap = round(atr * 0.5, 1)
    min_gap = 0.5
    max_gap = max(0.5, round(cp * 0.02, 1))
    price_gap = max(min_gap, min(raw_gap, max_gap))
    price_gap = round(price_gap, 1)

    # ── Batch size ─────────────────────────────────────────────────
    if free_qty <= 100:
        batch_size = 10
    elif free_qty <= 500:
        batch_size = 25
    elif free_qty <= 1000:
        batch_size = 50
    elif free_qty <= 5000:
        batch_size = 100
    else:
        batch_size = 250

    # Ensure we get at least 2 batches
    if batch_size > free_qty:
        batch_size = max(1, free_qty // 2)

    num_batches      = max(1, (free_qty + batch_size - 1) // batch_size)
    price_range_low  = base_trigger
    price_range_high = round(base_trigger + (num_batches - 1) * price_gap, 2)

    reasoning = (
        f"{reason_part}. "
        f"{num_batches} batch(es) × {batch_size} shares, "
        f"₹{price_range_low:.2f}→₹{price_range_high:.2f} "
        f"(gap ₹{price_gap:.1f}, ATR=₹{atr:.2f})."
    )

    log.info(
        "GTT suggestion: trigger=₹%.2f  gap=₹%.1f  batches=%d  batch_size=%d",
        base_trigger, price_gap, num_batches, batch_size,
    )

    return {
        "base_trigger"    : base_trigger,
        "price_gap"       : price_gap,
        "batch_size"      : batch_size,
        "num_batches"     : num_batches,
        "price_range_low" : price_range_low,
        "price_range_high": price_range_high,
        "reasoning"       : reasoning,
    }


# ─────────────────────────────────────────────────────────────────
# Private helper
# ─────────────────────────────────────────────────────────────────

def _last(series: "pd.Series") -> float:
    """Return the last non-NaN value of a pandas Series, or 0.0."""
    try:
        val = series.dropna().iloc[-1]
        return round(float(val), 4)
    except (IndexError, ValueError, TypeError):
        return 0.0
