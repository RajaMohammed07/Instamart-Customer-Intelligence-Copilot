from __future__ import annotations

import pandas as pd

from src.config import RAW_DIR


def audit_dataframe(df: pd.DataFrame, table_name: str) -> dict:
    blank_values = df.astype("string").apply(lambda column: column.str.strip().eq(""))
    missing_count = df.isna().sum().add(blank_values.sum(), fill_value=0).astype(int)
    missing_pct = (missing_count / len(df) * 100).round(2) if len(df) else missing_count
    return {
        "table_name": table_name,
        "rows": len(df),
        "columns": len(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing_count": missing_count.to_dict(),
        "missing_pct": missing_pct.to_dict(),
    }


def audit_raw_files() -> dict:
    tables = {}
    for name in ("customers", "products", "orders", "tickets"):
        frame = pd.read_csv(RAW_DIR / f"{name}.csv", keep_default_na=False)
        tables[name] = frame

    orders = tables["orders"]
    customers = tables["customers"]
    numeric_amounts = pd.to_numeric(orders["order_amount"], errors="coerce")
    numeric_delivery = pd.to_numeric(orders["delivery_minutes"], errors="coerce")
    numeric_age = pd.to_numeric(customers["age"], errors="coerce")
    nonblank_gender = customers["gender"].astype(str).str.strip().ne("")
    blank_amount = orders["order_amount"].astype(str).str.strip().eq("")
    exact_unique_orders = orders.drop_duplicates()

    summaries = {
        name: audit_dataframe(frame, name) for name, frame in tables.items()
    }
    summaries["raw_metrics"] = {
        "exact_duplicate_order_rows": int(orders.duplicated().sum()),
        "duplicate_order_id_rows_after_exact_dedup": int(
            exact_unique_orders.duplicated(subset="order_id").sum()
        ),
        "pending_order_rows": int(
            orders["status"].astype(str).str.strip().str.lower().eq("pending").sum()
        ),
        "distinct_order_ids": int(orders["order_id"].nunique()),
        "non_numeric_order_amounts": int(numeric_amounts.isna().sum()),
        "blank_order_amounts": int(blank_amount.sum()),
        "invalid_nonblank_order_amounts": int(
            (numeric_amounts.isna() & ~blank_amount).sum()
        ),
        "negative_delivery_times": int((numeric_delivery < 0).sum()),
        "blank_delivery_times": int(
            orders["delivery_minutes"].astype(str).str.strip().eq("").sum()
        ),
        "blank_customer_ages": int(
            customers["age"].astype(str).str.strip().eq("").sum()
        ),
        "ages_outside_10_100": int(((numeric_age < 10) | (numeric_age > 100)).sum()),
        "raw_city_spellings": int(customers["city"].nunique(dropna=False)),
        "raw_city_values": sorted(customers["city"].dropna().astype(str).unique().tolist()),
        "nonblank_gender_spellings": int(customers.loc[nonblank_gender, "gender"].nunique()),
        "nonblank_gender_values": sorted(
            customers.loc[nonblank_gender, "gender"].astype(str).unique().tolist()
        ),
        "blank_genders": int((~nonblank_gender).sum()),
        "order_ids_with_conflicting_statuses": int(
            (
                orders.groupby("order_id")["status"]
                .nunique()
                .gt(1)
                .sum()
            )
        ),
    }
    return summaries


def print_raw_audit(audit: dict) -> None:
    print("Raw data audit")
    for name in ("customers", "products", "orders", "tickets"):
        table = audit[name]
        print(f"  {name}: {table['rows']} rows x {table['columns']} columns")
        print(f"    dtypes: {table['dtypes']}")
        for column, count in table["missing_count"].items():
            print(f"    {column}: missing={count} ({table['missing_pct'][column]}%)")
    print("  Dirty-data metrics:")
    for metric, value in audit["raw_metrics"].items():
        print(f"    {metric}: {value}")
