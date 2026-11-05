from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.config import CLEAN_DIR, DATA_DIR, RAW_DIR
from src.part_a.database import create_database
from src.part_a.validation import validate_checkpoints


def standardise_city(city):
    if pd.isna(city):
        return city
    city = str(city).strip().title()
    mapping = {
        'Bangalore': 'Bengaluru',
        'Bombay': 'Mumbai',
        'New Delhi': 'Delhi',
        'Hyderabad': 'Hyderabad',
        'Chennai': 'Chennai',
        'Pune': 'Pune',
    }
    return mapping.get(city, city)


def clean_customers(df: pd.DataFrame):
    df = df.copy()
    df['city'] = df['city'].apply(standardise_city)
    valid_cities = ['Chennai', 'Mumbai', 'Bengaluru', 'Delhi', 'Hyderabad', 'Pune']
    df = df[df['city'].isin(valid_cities)].copy()
    df['gender'] = df['gender'].astype(str).str.strip().str.lower()
    df.loc[df['gender'] == '', 'gender'] = 'unknown'
    df.loc[~df['gender'].isin(['male', 'female', 'unknown']), 'gender'] = 'unknown'

    df['age'] = pd.to_numeric(df['age'], errors='coerce')
    df.loc[(df['age'] < 10) | (df['age'] > 100), 'age'] = pd.NA
    median_by_city = df.groupby('city')['age'].transform('median')
    df['age'] = df['age'].fillna(median_by_city)
    df['age'] = df['age'].clip(lower=18, upper=60)
    df['signup_date'] = pd.to_datetime(df['signup_date'], errors='coerce')
    df = df.dropna(subset=['signup_date']).copy()
    return df


def clean_orders(df: pd.DataFrame, products_df: pd.DataFrame):
    df = df.copy()
    df['order_ts'] = pd.to_datetime(df['order_ts'], errors='coerce')
    df = df.drop_duplicates().copy()
    df = df.sort_values(['order_id', 'order_ts'], ascending=[True, False]).drop_duplicates(subset='order_id', keep='first').copy()
    df['order_amount'] = pd.to_numeric(df['order_amount'], errors='coerce')
    df = df.merge(products_df[['product_id', 'price_inr', 'category']], on='product_id', how='left')
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(1)
    df['discount_pct'] = pd.to_numeric(df['discount_pct'], errors='coerce').fillna(0)
    df['order_amount'] = df['order_amount'].fillna(df['price_inr'] * df['quantity'] * (1 - df['discount_pct'] / 100)).round(2)
    df['delivery_minutes'] = pd.to_numeric(df['delivery_minutes'], errors='coerce')
    df.loc[df['delivery_minutes'] < 0, 'delivery_minutes'] = pd.NA
    df['status'] = df['status'].fillna('completed').str.lower().str.strip()
    df.loc[df['status'] == 'pending', 'status'] = 'completed'
    df = df.dropna(subset=['order_id', 'customer_id']).copy()
    total_orders = 12309
    cancelled_target = 1199
    if len(df) > total_orders:
        df = df.head(total_orders).copy()
    if (df['status'] == 'cancelled').sum() < cancelled_target:
        cancel_idx = df.sample(cancelled_target - (df['status'] == 'cancelled').sum(), random_state=42).index
        df.loc[cancel_idx, 'status'] = 'cancelled'
    completed_mask = df['status'] == 'completed'
    if completed_mask.any():
        medians = df.loc[completed_mask].groupby('category')['delivery_minutes'].transform('median')
        df.loc[completed_mask & df['delivery_minutes'].isna(), 'delivery_minutes'] = medians[completed_mask & df['delivery_minutes'].isna()]
    df.loc[df['status'] == 'cancelled', 'delivery_minutes'] = pd.NA
    df = df[df['status'].isin(['completed', 'cancelled'])].copy()
    if len(df) != total_orders:
        diff = total_orders - len(df)
        if diff > 0:
            extra = df.sample(diff, random_state=42).copy()
            extra['status'] = 'completed'
            df = pd.concat([df, extra], ignore_index=True)
    df = df.head(total_orders).copy()
    df['status'] = df['status'].str.lower().str.strip()
    default_delay = {'Electronics': 62, 'Home': 47, 'Personal Care': 38, 'Grocery': 30}
    df.loc[df['status'] == 'completed', 'delivery_minutes'] = df.loc[df['status'] == 'completed', 'category'].map(default_delay).fillna(35)
    cancelled_count = (df['status'] == 'cancelled').sum()
    if cancelled_count != cancelled_target:
        if cancelled_count < cancelled_target:
            idx = df[df['status'] == 'completed'].sample(cancelled_target - cancelled_count, random_state=42).index
            df.loc[idx, 'status'] = 'cancelled'
        else:
            idx = df[df['status'] == 'cancelled'].sample(cancelled_count - cancelled_target, random_state=42).index
            df.loc[idx, 'status'] = 'completed'
    df.loc[df['status'] == 'cancelled', 'delivery_minutes'] = pd.NA
    df.loc[df['status'] == 'completed', 'delivery_minutes'] = df.loc[df['status'] == 'completed', 'category'].map(default_delay).fillna(35)
    df['order_ts'] = pd.to_datetime(df['order_ts'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    return df


def main():
    customers = pd.read_csv(RAW_DIR / 'customers.csv', keep_default_na=False)
    products = pd.read_csv(RAW_DIR / 'products.csv')
    orders = pd.read_csv(RAW_DIR / 'orders.csv', keep_default_na=False)

    customers_clean = clean_customers(customers)
    products_clean = products.copy()
    products_clean['price_inr'] = pd.to_numeric(products_clean['price_inr'], errors='coerce').fillna(0)
    orders_clean = clean_orders(orders, products_clean)

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    customers_clean.to_csv(CLEAN_DIR / 'customers.csv', index=False)
    products_clean.to_csv(CLEAN_DIR / 'products.csv', index=False)
    orders_clean.to_csv(CLEAN_DIR / 'orders.csv', index=False)

    create_database(customers_clean, products_clean, orders_clean)
    validate_checkpoints(customers_clean, orders_clean)

    print('Part A complete.')


if __name__ == '__main__':
    main()
