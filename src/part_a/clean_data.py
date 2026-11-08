from __future__ import annotations

import pandas as pd

from src.config import CLEAN_DIR, DB_PATH, RAW_DIR
from src.part_a.data_audit import audit_raw_files, print_raw_audit
from src.part_a.database import create_database
from src.part_a.sql_analysis import main as run_sql_and_eda
from src.part_a.validation import validate_checkpoints

VALID_CITIES = {
    "Chennai",
    "Mumbai",
    "Bengaluru",
    "Delhi",
    "Hyderabad",
    "Pune",
}
CITY_ALIASES = {
    "Bangalore": "Bengaluru",
    "Bombay": "Mumbai",
    "New Delhi": "Delhi",
}
VALID_GENDERS = {"male", "female", "unknown"}


def standardise_city(city: object) -> object:
    if pd.isna(city):
        return pd.NA
    value = str(city).strip().title()
    return CITY_ALIASES.get(value, value)


def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    customers = df.copy()
    customers["city"] = customers["city"].map(standardise_city)

    gender = customers["gender"].astype("string").str.strip().str.lower()
    gender = gender.replace(
        {
            "": "unknown",
            "m": "male",
            "f": "female",
        }
    )
    customers["gender"] = gender.where(gender.isin(VALID_GENDERS), "unknown")

    customers["age"] = pd.to_numeric(customers["age"], errors="coerce")
    invalid_age = (customers["age"] < 10) | (customers["age"] > 100)
    customers.loc[invalid_age, "age"] = pd.NA
    city_age_median = customers.groupby("city")["age"].transform("median")
    customers["age"] = customers["age"].fillna(city_age_median).clip(18, 60)

    customers["signup_date"] = pd.to_datetime(
        customers["signup_date"], errors="coerce"
    )
    return customers


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    products = df.copy()
    products["price_inr"] = pd.to_numeric(products["price_inr"], errors="coerce")
    return products


def clean_orders(df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
    orders = df.copy()
    orders["order_ts"] = pd.to_datetime(orders["order_ts"], errors="coerce")
    if orders["order_ts"].isna().any():
        invalid_count = int(orders["order_ts"].isna().sum())
        raise ValueError(f"{invalid_count} raw order timestamps are invalid.")

    orders = orders.drop_duplicates().copy()
    orders = (
        orders.sort_values(["order_id", "order_ts"], kind="mergesort")
        .drop_duplicates(subset="order_id", keep="last")
        .copy()
    )
    orders["order_amount"] = pd.to_numeric(orders["order_amount"], errors="coerce")

    products_for_merge = products_df[["product_id", "price_inr", "category"]]
    orders = orders.merge(
        products_for_merge,
        on="product_id",
        how="left",
        validate="many_to_one",
    )
    orders["quantity"] = pd.to_numeric(orders["quantity"], errors="coerce")
    orders["discount_pct"] = pd.to_numeric(orders["discount_pct"], errors="coerce")
    calculated_amount = (
        orders["price_inr"]
        * orders["quantity"]
        * (1 - orders["discount_pct"] / 100)
    ).round(2)
    orders["order_amount"] = orders["order_amount"].fillna(calculated_amount).round(2)

    orders["delivery_minutes"] = pd.to_numeric(
        orders["delivery_minutes"], errors="coerce"
    )
    orders.loc[orders["delivery_minutes"] < 0, "delivery_minutes"] = pd.NA
    orders["status"] = orders["status"].astype("string").str.strip().str.lower()

    completed = orders["status"].eq("completed")
    completed_category_medians = orders.loc[completed].groupby("category")[
        "delivery_minutes"
    ].transform("median")
    orders.loc[completed, "delivery_minutes"] = orders.loc[
        completed, "delivery_minutes"
    ].fillna(completed_category_medians)

    cancelled = orders["status"].eq("cancelled")
    orders.loc[cancelled, "delivery_minutes"] = pd.NA
    orders["order_ts"] = orders["order_ts"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return orders


def main() -> None:
    audit = audit_raw_files()
    print_raw_audit(audit)

    customers_raw = pd.read_csv(RAW_DIR / "customers.csv", keep_default_na=False)
    products_raw = pd.read_csv(RAW_DIR / "products.csv", keep_default_na=False)
    orders_raw = pd.read_csv(RAW_DIR / "orders.csv", keep_default_na=False)

    customers = clean_customers(customers_raw)
    products = clean_products(products_raw)
    orders = clean_orders(orders_raw, products)

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    customers.to_csv(CLEAN_DIR / "customers.csv", index=False)
    products.to_csv(CLEAN_DIR / "products.csv", index=False)
    orders.to_csv(CLEAN_DIR / "orders.csv", index=False)

    create_database(customers, products, orders)
    print("Clean customer city counts:", customers["city"].value_counts().to_dict())
    print("Clean customer gender counts:", customers["gender"].value_counts().to_dict())
    print("Clean order status counts:", orders["status"].value_counts().to_dict())
    completed = orders["status"].eq("completed")
    cancelled = orders["status"].eq("cancelled")
    print(
        "Clean completed order amount total: "
        f"INR {orders.loc[completed, 'order_amount'].sum():,.2f}"
    )
    print(
        "Missing delivery times - completed: "
        f"{int(orders.loc[completed, 'delivery_minutes'].isna().sum())}; "
        "cancelled: "
        f"{int(orders.loc[cancelled, 'delivery_minutes'].isna().sum())}"
    )
    validation = validate_checkpoints(
        customers,
        products,
        orders,
        raw_orders=orders_raw,
        raw_customer_count=len(customers_raw),
        distinct_raw_order_count=int(orders_raw["order_id"].nunique()),
        database_path=DB_PATH,
    )
    if not validation["passed"]:
        print("Part A validation has failures; reference mismatches are reported above.")
    else:
        print("ALL CHECKPOINTS PASSED")

    run_sql_and_eda()
    if not validation["passed"]:
        raise SystemExit("Part A finished with failed data-quality/reference checks.")
    print("Part A complete.")


if __name__ == "__main__":
    main()
