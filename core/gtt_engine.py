"""
core/gtt_engine.py
==================
Staggered GTT order mathematics and background execution engine.

Math
----
    num_orders = total_shares // batch_size
    For tier i in range(0, num_orders):
        trigger_price = base_trigger + (i * price_gap)
        limit_price   = trigger_price - limit_offset
        quantity      = batch_size
    Edge case: if total_shares % batch_size != 0, add a final partial batch.

Execution
---------
    Runs in a background threading.Thread.
    Checks stop_event each iteration — Abort button sets it.
    Sleeps 0.2 s per order (ICICI rate limit: max 10 req/sec combined).
    Calls back to the UI thread-safely via log_callback & progress_callback.
"""

from __future__ import annotations

import time
import threading
import json
from dataclasses import dataclass, field
from typing import Callable, Any

from core.breeze_client import place_gtt_single_leg, BreezeAPIError


# -----------------------------------------------------------------
# Data model for a single planned GTT batch
# -----------------------------------------------------------------

@dataclass
class GTTOrder:
    """Represents one batch (tier) in the staggered GTT plan."""
    batch_number:  int
    stock_code:    str
    exchange_code: str
    trigger_price: float
    limit_price:   float
    quantity:      int
    action:        str = "sell"


# -----------------------------------------------------------------
# Math: calculate the staggered order list
# -----------------------------------------------------------------

def calculate_orders(
    stock_code:    str,
    exchange_code: str,
    total_shares:  int,
    batch_size:    int,
    base_trigger:  float,
    price_gap:     float,
    limit_offset:  float,
    action:        str = "sell",
    algorithm:     str = "LINEAR",
) -> list[GTTOrder]:
    """
    Compute the full list of GTTOrder objects for the staggered plan.

    Parameters
    ----------
    stock_code    : BSE/NSE stock symbol (e.g. "RELIANCE").
    exchange_code : "NSE" or "BSE".
    total_shares  : Total number of shares to sell/buy via GTT.
    batch_size    : Base shares per GTT order.
    base_trigger  : Trigger price for the first batch (₹).
    price_gap     : Price increment between consecutive batches (₹).
    limit_offset  : Amount subtracted from trigger to get limit price (₹).
                    Use a positive value for a sell buffer below trigger.
    action        : "sell" or "buy" (default "sell").
    algorithm     : "LINEAR", "PYRAMID", or "MARTINGALE".

    Returns
    -------
    Ordered list of GTTOrder dataclass instances.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be a positive integer.")
    if total_shares <= 0:
        raise ValueError("total_shares must be a positive integer.")
    if batch_size > total_shares:
        raise ValueError("batch_size cannot exceed total_shares.")
    if base_trigger <= 0:
        raise ValueError("base_trigger must be a positive price.")

    orders: list[GTTOrder] = []
    
    batch_sizes = []
    shares_remaining = total_shares
    current_multiplier = 1
    
    while shares_remaining > 0:
        current_batch = batch_size * current_multiplier
        if current_batch > shares_remaining:
            current_batch = shares_remaining
            
        batch_sizes.append(current_batch)
        shares_remaining -= current_batch
        
        if algorithm.upper() == "PYRAMID":
            current_multiplier += 1
        elif algorithm.upper() == "MARTINGALE":
            current_multiplier *= 2

    for i, qty in enumerate(batch_sizes):
        trigger = round(base_trigger + i * price_gap, 2)
        limit   = round(trigger - limit_offset, 2)
        orders.append(GTTOrder(
            batch_number  = i + 1,
            stock_code    = stock_code,
            exchange_code = exchange_code,
            trigger_price = trigger,
            limit_price   = limit,
            quantity      = qty,
            action        = action,
        ))

    return orders


# -----------------------------------------------------------------
# Execution result container
# -----------------------------------------------------------------

@dataclass
class ExecutionSummary:
    total:   int = 0
    success: int = 0
    failed:  int = 0
    skipped: int = 0
    aborted: bool = False


# -----------------------------------------------------------------
# Main execution loop (runs in a background thread)
# -----------------------------------------------------------------

def place_staggered_gtt(
    breeze: Any,
    order_list: list[GTTOrder],
    client_name: str,
    stop_event: threading.Event,
    log_callback: Callable[[str], None],
    progress_callback: Callable[[int, int], None],
    db_log_func: Callable[..., None],
) -> ExecutionSummary:
    """
    Execute the staggered GTT placement loop in a background thread.

    Parameters
    ----------
    breeze            : Authenticated BreezeConnect instance.
    order_list        : Output of calculate_orders().
    client_name       : For DB logging.
    stop_event        : threading.Event — set by Abort button.
    log_callback      : Callable(msg: str) — appends text to the UI console.
                        Must be thread-safe (use CTk after() internally).
    progress_callback : Callable(current: int, total: int) — updates progress bar.
    db_log_func       : Reference to database.log_order().

    Returns
    -------
    ExecutionSummary with counts of success / failed / skipped.
    """
    summary = ExecutionSummary(total=len(order_list))
    total = len(order_list)

    log_callback(f"━━━ Starting GTT Execution: {total} batch(es) for "
                 f"{order_list[0].stock_code if order_list else 'N/A'} ━━━")

    for i, order in enumerate(order_list):

        # ── Check abort flag before every order ──
        if stop_event.is_set():
            log_callback(f"\n⛔ Execution aborted by user after {i} batch(es).")
            summary.aborted = True
            summary.skipped += (total - i)
            # Log remaining as SKIPPED
            for j in range(i, total):
                _safe_db_log(db_log_func, client_name, order_list[j], "SKIPPED", None)
            break

        log_callback(
            f"\n[Batch {order.batch_number}/{total}]  "
            f"{order.stock_code} | {order.action.upper()} {order.quantity} qty | "
            f"Trigger ₹{order.trigger_price:.2f} → Limit ₹{order.limit_price:.2f}"
        )

        # ── Place the GTT order ──
        response: dict | None = None
        try:
            response = place_gtt_single_leg(
                breeze        = breeze,
                stock_code    = order.stock_code,
                exchange_code = order.exchange_code,
                trigger_price = order.trigger_price,
                limit_price   = order.limit_price,
                quantity      = order.quantity,
                action        = order.action,
            )

            status_code = response.get("Status")

            if status_code == 200:
                success_data = response.get("Success", {})
                order_id = (
                    success_data.get("order_id")
                    or success_data.get("orderId")
                    or "N/A"
                    if isinstance(success_data, dict)
                    else "N/A"
                )
                log_callback(
                    f"  ✅ SUCCESS — Order ID: {order_id}"
                )
                _safe_db_log(db_log_func, client_name, order, "SUCCESS", response)
                summary.success += 1

            else:
                error_msg = (
                    response.get("Error")
                    or response.get("Message")
                    or str(response)
                )
                log_callback(f"  ⚠️  REJECTED — {error_msg}")
                _safe_db_log(db_log_func, client_name, order, "FAILED", response)
                summary.failed += 1

        except BreezeAPIError as exc:
            log_callback(f"  ❌ EXCEPTION — {exc}")
            _safe_db_log(db_log_func, client_name, order, "SKIPPED",
                         {"exception": str(exc)})
            summary.skipped += 1

        except Exception as exc:
            log_callback(f"  ❌ UNEXPECTED ERROR — {exc}")
            _safe_db_log(db_log_func, client_name, order, "SKIPPED",
                         {"exception": str(exc)})
            summary.skipped += 1

        # ── Update progress bar ──
        progress_callback(i + 1, total)

        # ── ICICI rate limit: ≤ 10 req/sec (0.2s gap = safe) ──
        if i < total - 1:
            time.sleep(0.2)

    # ── Final summary ──
    if not summary.aborted:
        log_callback(
            f"\n━━━ Execution Complete ━━━\n"
            f"  ✅ Success : {summary.success}\n"
            f"  ⚠️  Failed  : {summary.failed}\n"
            f"  ❌ Skipped : {summary.skipped}\n"
            f"  Total     : {summary.total}"
        )

    return summary


# -----------------------------------------------------------------
# Private helper — safe DB logging (never crashes the execution loop)
# -----------------------------------------------------------------

def _safe_db_log(
    db_log_func: Callable[..., None],
    client_name: str,
    order: GTTOrder,
    status: str,
    response: dict | None,
) -> None:
    try:
        db_log_func(
            client_name   = client_name,
            stock_code    = order.stock_code,
            batch_number  = order.batch_number,
            trigger_price = order.trigger_price,
            quantity      = order.quantity,
            status        = status,
            response_data = response,
        )
    except Exception:
        pass  # Never crash the execution loop due to a logging failure
