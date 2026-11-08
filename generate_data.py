from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
CUSTOMERS_PATH = RAW_DIR / "customers.csv"
ORDERS_PATH = RAW_DIR / "orders.csv"
PRODUCTS_PATH = RAW_DIR / "products.csv"

ORDER_WINDOW_START = pd.Timestamp("2025-04-01 00:00:00")
ORDER_WINDOW_END = pd.Timestamp("2025-09-30 23:59:59")
SIGNUP_LEAD_TIME_SEED = 43
SIGNUP_LEAD_TIME_MAX_DAYS = 365


def _read_raw_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Canonical raw data file not found: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def transform_order_timestamps(orders: pd.DataFrame) -> pd.DataFrame:
    """Map source timestamps monotonically into the assignment window."""
    transformed = orders.copy()
    parsed = pd.to_datetime(transformed["order_ts"], errors="raise")
    if parsed.empty:
        raise ValueError("Cannot transform an empty order table.")
    if parsed.between(ORDER_WINDOW_START, ORDER_WINDOW_END).all():
        return transformed

    source_start = parsed.min()
    source_end = parsed.max()
    source_span = source_end.value - source_start.value
    target_span = ORDER_WINDOW_END.value - ORDER_WINDOW_START.value
    if source_span <= 0:
        raise ValueError("Order timestamps must span at least two distinct values.")

    target_ns = [
        ORDER_WINDOW_START.value
        + (int(timestamp.value - source_start.value) * target_span // source_span)
        for timestamp in parsed
    ]
    mapped = pd.Series(pd.to_datetime(target_ns), index=orders.index)

    timestamp_map = pd.DataFrame(
        {"source": parsed, "mapped": mapped}
    ).drop_duplicates("source")
    timestamp_map = timestamp_map.sort_values("source")
    if not timestamp_map["mapped"].is_monotonic_increasing:
        raise ValueError("Timestamp transformation did not preserve source ordering.")
    if timestamp_map["mapped"].duplicated().any():
        raise ValueError(
            "Timestamp transformation collapsed distinct source timestamps."
        )
    if not mapped.between(ORDER_WINDOW_START, ORDER_WINDOW_END).all():
        raise AssertionError("Transformed timestamps fall outside the target window.")

    transformed["order_ts"] = mapped.dt.strftime("%Y-%m-%d %H:%M:%S")
    return transformed


def generate_signup_dates(
    customers: pd.DataFrame, orders: pd.DataFrame
) -> pd.DataFrame:
    """Assign seeded 0-365 day lead times before each first non-pending order."""
    transformed = customers.copy()
    order_times = pd.to_datetime(orders["order_ts"], errors="raise")
    non_pending = orders["status"].str.strip().str.lower().ne("pending")
    final_orders = orders.loc[non_pending].assign(_order_ts=order_times.loc[non_pending])
    first_order_dates = final_orders.groupby("customer_id")["_order_ts"].min()

    missing_customers = sorted(set(transformed["customer_id"]) - set(first_order_dates.index))
    if missing_customers:
        raise ValueError(
            "No non-pending order exists for customer(s): "
            + ", ".join(missing_customers[:10])
        )

    rng = random.Random(SIGNUP_LEAD_TIME_SEED)
    signup_dates = []
    for customer_id in transformed["customer_id"]:
        first_order = first_order_dates.loc[customer_id].normalize()
        lead_days = rng.randint(0, SIGNUP_LEAD_TIME_MAX_DAYS)
        signup_dates.append((first_order - pd.Timedelta(days=lead_days)).strftime("%Y-%m-%d"))
    transformed["signup_date"] = signup_dates
    return transformed


def _write_csv_atomically(frame: pd.DataFrame, path: Path) -> None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary_path, index=False)
    temporary_path.replace(path)


def main() -> None:
    customers = _read_raw_csv(CUSTOMERS_PATH)
    orders = _read_raw_csv(ORDERS_PATH)
    _read_raw_csv(PRODUCTS_PATH)

    dated_orders = transform_order_timestamps(orders)
    dated_customers = generate_signup_dates(customers, dated_orders)

    unchanged_order_columns = [
        column for column in orders.columns if column != "order_ts"
    ]
    if not orders[unchanged_order_columns].equals(
        dated_orders[unchanged_order_columns]
    ):
        raise AssertionError("Order transformation changed a non-date field.")
    unchanged_customer_columns = [
        column for column in customers.columns if column != "signup_date"
    ]
    if not customers[unchanged_customer_columns].equals(
        dated_customers[unchanged_customer_columns]
    ):
        raise AssertionError("Signup transformation changed a non-date field.")

    _write_csv_atomically(dated_orders, ORDERS_PATH)
    _write_csv_atomically(dated_customers, CUSTOMERS_PATH)
    print(
        "Updated only order_ts and signup_date from the canonical raw CSV snapshot; "
        "customer attributes, product data, and order business fields were preserved."
    )


if __name__ == "__main__":
    main()
