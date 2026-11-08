from __future__ import annotations

import math
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from src.config import DB_PATH


def _connect_read_only(db_path: Path | None = None) -> sqlite3.Connection:
    path = (db_path or DB_PATH).resolve()
    return sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)


def get_order(order_id: str, customer_id: str) -> dict[str, Any]:
    if not order_id or not customer_id:
        raise ValueError("Both order_id and customer_id are required")

    with closing(_connect_read_only()) as connection:
        row = connection.execute(
            """
            SELECT order_id, status, order_amount, delivery_minutes, order_ts
            FROM orders
            WHERE order_id = ? AND customer_id = ?
            """,
            (order_id, customer_id),
        ).fetchone()

    if row is None:
        return {"error": "order not found or customer verification failed"}
    return {
        "order_id": row[0],
        "status": row[1],
        "order_amount": row[2],
        "delivery_minutes": row[3],
        "order_ts": row[4],
    }


def calculate_refund(
    order_amount: float | None, delivery_minutes: float | None
) -> dict[str, float]:
    if order_amount is None or delivery_minutes is None:
        raise ValueError("Verified order amount and delivery measurement are required")
    amount = float(order_amount)
    delivery = float(delivery_minutes)
    if not math.isfinite(amount) or not math.isfinite(delivery):
        raise ValueError("Order amount and delivery time must be finite values")
    if amount <= 0 or delivery < 0:
        raise ValueError("Order amount must be positive and delivery time nonnegative")
    refund = amount if delivery > 45 else 0.0
    return {"refund_inr": round(refund, 2)}


def escalate_to_human(reason: str, target: str) -> dict[str, Any]:
    if not reason.strip() or not target.strip():
        raise ValueError("A handoff reason and target are required")
    return {
        "status": "HANDOFF_REQUIRED",
        "target": target,
        "reason": reason,
        "external_action_taken": False,
    }
