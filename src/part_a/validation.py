from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


def validate_checkpoints(
    customers: pd.DataFrame,
    products: pd.DataFrame,
    orders: pd.DataFrame,
    raw_orders: pd.DataFrame,
    raw_customer_count: int,
    distinct_raw_order_count: int,
    database_path: Path,
) -> dict:
    completed = orders["status"].eq("completed")
    cancelled = orders["status"].eq("cancelled")

    checks: list[tuple[str, bool, object, object]] = []

    def add(name: str, passed: bool, actual: object, expected: object) -> None:
        checks.append((name, bool(passed), actual, expected))

    add(
        "Customer rows preserved",
        len(customers) == raw_customer_count,
        len(customers),
        raw_customer_count,
    )
    add(
        "Exactly the six supported cities",
        set(customers["city"].dropna().unique())
        == {"Chennai", "Mumbai", "Bengaluru", "Delhi", "Hyderabad", "Pune"},
        sorted(customers["city"].dropna().unique().tolist()),
        ["Bengaluru", "Chennai", "Delhi", "Hyderabad", "Mumbai", "Pune"],
    )
    add(
        "Gender values standardized",
        set(customers["gender"].dropna().unique()).issubset(
            {"male", "female", "unknown"}
        ),
        sorted(customers["gender"].dropna().unique().tolist()),
        ["female", "male", "unknown"],
    )
    add(
        "Customer ages present and in range 18-60",
        customers["age"].notna().all() and customers["age"].between(18, 60).all(),
        {
            "missing": int(customers["age"].isna().sum()),
            "min": customers["age"].min(),
            "max": customers["age"].max(),
        },
        "no missing ages; minimum >= 18; maximum <= 60",
    )
    add(
        "Signup dates parsed",
        pd.to_datetime(customers["signup_date"], errors="coerce").notna().all(),
        int(pd.to_datetime(customers["signup_date"], errors="coerce").isna().sum()),
        "0 invalid dates",
    )
    order_timestamps = pd.to_datetime(orders["order_ts"], errors="coerce")
    add(
        "Order dates within 2025-04-01 through 2025-09-30",
        order_timestamps.notna().all()
        and order_timestamps.ge(pd.Timestamp("2025-04-01")).all()
        and order_timestamps.lt(pd.Timestamp("2025-10-01")).all(),
        {
            "min": order_timestamps.min(),
            "max": order_timestamps.max(),
        },
        "2025-04-01 <= order_ts < 2025-10-01",
    )
    signup_dates = pd.to_datetime(customers["signup_date"], errors="coerce")
    final_order_mask = orders["status"].astype("string").str.lower().ne("pending")
    first_orders = (
        orders.loc[final_order_mask]
        .assign(_parsed_order_ts=order_timestamps.loc[final_order_mask])
        .groupby("customer_id")["_parsed_order_ts"]
        .min()
        .rename("first_order_ts")
        .reset_index()
    )
    chronology = customers[["customer_id"]].assign(
        signup_date=signup_dates
    ).merge(first_orders, on="customer_id", how="left", validate="one_to_one")
    signup_before_first_order = (
        chronology["first_order_ts"].notna()
        & chronology["signup_date"].notna()
        & chronology["signup_date"].le(chronology["first_order_ts"])
    )
    add(
        "Signup date on or before first order",
        signup_before_first_order.all(),
        int((~signup_before_first_order).sum()),
        "0 customers signed up after first order",
    )
    cutoff = pd.Timestamp("2025-09-01")
    eligible_customer_ids = set(
        orders.loc[
            orders["status"].eq("completed") & order_timestamps.lt(cutoff),
            "customer_id",
        ]
    )
    eligible = chronology.loc[chronology["customer_id"].isin(eligible_customer_ids)]
    tenure_days = (cutoff - eligible["signup_date"]).dt.days
    add(
        "Eligible customer tenure nonnegative at lapse cutoff",
        tenure_days.notna().all() and tenure_days.ge(0).all(),
        {
            "eligible_customers": len(eligible),
            "missing_tenure": int(tenure_days.isna().sum()),
            "negative_tenure": int(tenure_days.lt(0).sum()),
        },
        "all pre-cutoff completed-order customers have nonnegative tenure",
    )
    add(
        "Clean orders match distinct raw order IDs",
        len(orders) == distinct_raw_order_count,
        len(orders),
        distinct_raw_order_count,
    )
    add(
        "Order IDs unique",
        orders["order_id"].is_unique,
        int(orders["order_id"].duplicated().sum()),
        "0 duplicate IDs",
    )
    add(
        "Allowed final statuses only",
        set(orders["status"].dropna().unique()).issubset(
            {"completed", "cancelled", "pending"}
        ),
        orders["status"].value_counts(dropna=False).to_dict(),
        "completed, cancelled, or pending",
    )
    add(
        "Order amounts present",
        orders["order_amount"].notna().all(),
        int(orders["order_amount"].isna().sum()),
        "0 missing amounts",
    )
    add(
        "Order timestamps use YYYY-MM-DD HH:MM:SS",
        orders["order_ts"].map(
            lambda value: isinstance(value, str)
            and pd.notna(
                parsed := pd.to_datetime(
                    value, format="%Y-%m-%d %H:%M:%S", errors="coerce"
                )
            )
            and parsed.strftime("%Y-%m-%d %H:%M:%S") == value
        ).all(),
        orders["order_ts"].head(3).tolist(),
        "all timestamps formatted to seconds",
    )
    add(
        "Negative delivery times removed",
        not (orders["delivery_minutes"].dropna() < 0).any(),
        int((orders["delivery_minutes"].dropna() < 0).sum()),
        "0 negative values",
    )
    completed_orders = orders.loc[completed]
    raw_completed = raw_orders.loc[
        raw_orders["status"].astype("string").str.strip().str.lower().eq("completed")
    ].copy()
    raw_completed["delivery_minutes"] = pd.to_numeric(
        raw_completed["delivery_minutes"], errors="coerce"
    )
    raw_completed = raw_completed.merge(
        products[["product_id", "category"]],
        on="product_id",
        how="left",
        validate="many_to_one",
    )
    valid_delivery_categories = set(
        raw_completed.loc[
            raw_completed["delivery_minutes"].ge(0), "category"
        ].dropna()
    )
    categories_without_measurements = set(
        completed_orders["category"].dropna()
    ) - valid_delivery_categories
    expected_unimputable = int(
        completed_orders["category"].isin(categories_without_measurements).sum()
    )
    actual_missing_completed = int(
        completed_orders["delivery_minutes"].isna().sum()
    )
    add(
        "Missing completed delivery values limited to categories without source measurements",
        actual_missing_completed == expected_unimputable,
        {
            "missing_completed_values": actual_missing_completed,
            "categories_without_valid_measurements": sorted(
                categories_without_measurements
            ),
        },
        {
            "unimputable_values": expected_unimputable,
            "rule": "retain missing values only if raw completed orders have no valid measurement in category",
        },
    )
    add(
        "Cancelled orders retain missing delivery times",
        orders.loc[cancelled, "delivery_minutes"].isna().all(),
        int(orders.loc[cancelled, "delivery_minutes"].notna().sum()),
        "0 non-missing cancelled-order delivery times",
    )
    add(
        "Product lookup resolved",
        orders["price_inr"].notna().all()
        and orders["category"].notna().all()
        and products["product_id"].is_unique,
        {
            "orders_missing_price": int(orders["price_inr"].isna().sum()),
            "orders_missing_category": int(orders["category"].isna().sum()),
            "duplicate_product_ids": int(products["product_id"].duplicated().sum()),
        },
        "all order products resolved; unique product IDs",
    )

    try:
        with sqlite3.connect(database_path) as connection:
            table_names = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            required_tables = {"customers", "products", "orders"}
            add(
                "SQLite tables created",
                required_tables.issubset(table_names),
                sorted(table_names),
                sorted(required_tables),
            )
            stored_timestamps = [
                row[0]
                for row in connection.execute(
                    "SELECT order_ts FROM orders LIMIT 5"
                )
            ]
            timestamp_format_ok = all(
                pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S") == value
                for value in stored_timestamps
            )
            add(
                "SQLite order timestamps stored as text",
                timestamp_format_ok,
                stored_timestamps,
                "YYYY-MM-DD HH:MM:SS",
            )
    except sqlite3.Error as error:
        add("SQLite database readable", False, str(error), "readable SQLite database")

    print("Part A validation")
    for name, passed, actual, expected in checks:
        label = "PASS" if passed else "FAIL"
        print(f"  {label} - {name}: actual={actual!r}; expected={expected!r}")

    return {
        "passed": all(passed for _, passed, _, _ in checks),
        "checks": checks,
    }
