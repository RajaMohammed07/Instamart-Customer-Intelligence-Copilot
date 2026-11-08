from __future__ import annotations

import sqlite3

import pandas as pd

from src.config import DB_PATH


def load_part_b_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the current generated customer and order tables from SQLite."""
    with sqlite3.connect(DB_PATH) as connection:
        customers = pd.read_sql_query("SELECT * FROM customers", connection)
        orders = pd.read_sql_query("SELECT * FROM orders", connection)
    return orders, customers


def compute_rfm(
    orders: pd.DataFrame,
    customers: pd.DataFrame,
    snapshot: str = "2025-10-01",
) -> pd.DataFrame:
    snapshot_ts = pd.Timestamp(snapshot)
    completed = orders.loc[orders["status"].eq("completed")].copy()
    completed["order_ts"] = pd.to_datetime(completed["order_ts"], errors="raise")
    completed = completed.loc[completed["order_ts"].lt(snapshot_ts)]
    rfm = completed.groupby("customer_id").agg(
        recency=("order_ts", lambda values: (snapshot_ts - values.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("order_amount", "sum"),
    )
    result = customers[["customer_id"]].merge(
        rfm,
        on="customer_id",
        how="left",
        validate="one_to_one",
    )
    result["frequency"] = result["frequency"].fillna(0).astype(int)
    result["monetary"] = result["monetary"].fillna(0.0)
    return result.sort_values("customer_id").reset_index(drop=True)


def rfm_summary(rfm: pd.DataFrame):
    return {
        "customers": int(rfm["customer_id"].nunique()),
        "recency_median": float(rfm["recency"].median()),
        "recency_min": float(rfm["recency"].min()),
        "recency_max": float(rfm["recency"].max()),
        "frequency_mean": float(rfm["frequency"].mean()),
        "frequency_max": int(rfm["frequency"].max()),
        "monetary_mean": float(rfm["monetary"].mean()),
        "monetary_max": float(rfm["monetary"].max()),
    }


def identify_premium_customers(rfm: pd.DataFrame) -> pd.Series:
    return (
        rfm["monetary"].ge(rfm["monetary"].quantile(0.80))
        & rfm["frequency"].ge(rfm["frequency"].median())
        & rfm["recency"].le(rfm["recency"].median())
    )
