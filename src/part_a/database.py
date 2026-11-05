from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.config import DATA_DIR, DB_PATH


def create_database(df_customers: pd.DataFrame, df_products: pd.DataFrame, df_orders: pd.DataFrame):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    df_customers.to_sql('customers', conn, index=False, if_exists='replace')
    df_products.to_sql('products', conn, index=False, if_exists='replace')
    df_orders.to_sql('orders', conn, index=False, if_exists='replace')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_orders_order_ts ON orders(order_ts)')
    conn.commit()
    conn.close()
    return DB_PATH
