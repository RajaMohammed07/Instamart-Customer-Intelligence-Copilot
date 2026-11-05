from __future__ import annotations

from typing import Any

import pandas as pd


def audit_dataframe(df: pd.DataFrame, table_name: str) -> dict:
    missing = df.isna().sum().to_dict()
    missing_pct = (df.isna().mean() * 100).round(2).to_dict()
    return {
        'table_name': table_name,
        'rows': len(df),
        'columns': len(df.columns),
        'dtypes': df.dtypes.astype(str).to_dict(),
        'missing_count': missing,
        'missing_pct': missing_pct,
    }


def audit_raw_files():
    raw = {}
    for name in ['customers', 'products', 'orders']:
        df = pd.read_csv(f'data/raw/{name}.csv', keep_default_na=False)
        raw[name] = audit_dataframe(df, name)
    tickets = pd.read_csv('data/raw/tickets.csv', keep_default_na=False)
    raw['tickets'] = audit_dataframe(tickets, 'tickets')
    return raw
