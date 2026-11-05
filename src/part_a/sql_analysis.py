from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.config import DB_PATH


def run_sql_queries():
    conn = sqlite3.connect(DB_PATH)
    sql_text = Path('sql/queries.sql').read_text(encoding='utf-8')
    queries = [q.strip() for q in sql_text.split(';') if q.strip()]
    results = []
    for idx, query in enumerate(queries, start=1):
        df = pd.read_sql_query(query, conn)
        results.append({'query_id': idx, 'rows': len(df), 'data': df})
    conn.close()
    return results


def main():
    results = run_sql_queries()
    print('Executed', len(results), 'queries.')
    return results


if __name__ == '__main__':
    main()
