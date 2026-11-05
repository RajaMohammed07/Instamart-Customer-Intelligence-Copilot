from __future__ import annotations

from datetime import datetime

import pandas as pd


def compute_rfm(orders: pd.DataFrame, customers: pd.DataFrame, snapshot: str = '2025-10-01 00:00:00') -> pd.DataFrame:
    snapshot_ts = pd.Timestamp(snapshot)
    completed = orders[orders['status'] == 'completed'].copy()
    completed['order_ts'] = pd.to_datetime(completed['order_ts'])
    rfm = completed.groupby('customer_id').agg(
        recency=('order_ts', lambda s: (snapshot_ts - s.max()).days),
        frequency=('order_id', 'nunique'),
        monetary=('order_amount', 'sum'),
    ).reset_index()
    return rfm.merge(customers[['customer_id']], on='customer_id', how='inner')


def rfm_summary(rfm: pd.DataFrame):
    return {
        'customers': int(rfm['customer_id'].nunique()),
        'recency_median': float(rfm['recency'].median()),
        'recency_min': float(rfm['recency'].min()),
        'recency_max': float(rfm['recency'].max()),
        'frequency_mean': float(rfm['frequency'].mean()),
        'frequency_max': int(rfm['frequency'].max()),
        'monetary_mean': float(rfm['monetary'].mean()),
        'monetary_max': float(rfm['monetary'].max()),
    }
