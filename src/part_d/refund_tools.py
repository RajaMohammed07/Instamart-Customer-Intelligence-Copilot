from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from src.config import DB_PATH
from src.part_d.policy_retrieval import retrieve_policy

LEDGER_PATH = Path('outputs/refund_ledger.jsonl')


def get_order(order_id: str):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        'SELECT order_id, status, order_amount, delivery_minutes FROM orders WHERE order_id=?',
        (order_id,)
    ).fetchone()
    conn.close()
    if not row:
        return {'error': 'order not found'}
    return {'order_id': row[0], 'status': row[1], 'order_amount': row[2], 'delivery_minutes': row[3]}


def search_policy(query: str):
    return retrieve_policy(query, k=3)


def calculate_refund(order_amount, delivery_minutes):
    amount = float(order_amount or 0)
    delivery = float(delivery_minutes or 0)
    refund = amount if delivery > 45 else 0.0
    return {'refund_inr': round(refund, 2)}


def issue_refund(order_id: str, refund_inr: float):
    LEDGER_PATH.parent.mkdir(exist_ok=True)
    record = {'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'), 'tool': 'issue_refund', 'order_id': order_id, 'refund_inr': float(refund_inr)}
    with LEDGER_PATH.open('a', encoding='utf-8') as f:
        f.write(json.dumps(record) + '\n')
    return {'refund_inr': float(refund_inr)}


def escalate_to_human(order_id: str, refund_inr: float):
    LEDGER_PATH.parent.mkdir(exist_ok=True)
    record = {'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'), 'tool': 'escalate_to_human', 'order_id': order_id, 'refund_inr': float(refund_inr)}
    with LEDGER_PATH.open('a', encoding='utf-8') as f:
        f.write(json.dumps(record) + '\n')
    return {'refund_inr': float(refund_inr)}
