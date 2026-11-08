from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import CLEAN_DIR, DB_PATH, ROOT


def run_sql_queries() -> list[dict]:
    sql_path = ROOT / "sql" / "queries.sql"
    with sqlite3.connect(DB_PATH) as connection:
        sql_text = sql_path.read_text(encoding="utf-8")
        statements = [statement.strip() for statement in sql_text.split(";") if statement.strip()]
        return [
            {
                "query_id": index,
                "rows": len(frame := pd.read_sql_query(statement, connection)),
                "data": frame,
            }
            for index, statement in enumerate(statements, start=1)
        ]


def run_pandas_analysis(sql_results: list[dict]) -> dict:
    customers = pd.read_csv(CLEAN_DIR / "customers.csv")
    products = pd.read_csv(CLEAN_DIR / "products.csv")
    orders = pd.read_csv(CLEAN_DIR / "orders.csv")
    completed = orders.loc[orders["status"].eq("completed")].copy()
    if "category" in completed.columns:
        completed = completed.drop(columns="category")
    completed = completed.merge(
        customers[["customer_id", "city"]],
        on="customer_id",
        how="left",
        validate="many_to_one",
    )
    completed = completed.merge(
        products[["product_id", "category"]],
        on="product_id",
        how="left",
        validate="many_to_one",
    )

    pivot = pd.pivot_table(
        completed,
        values="order_amount",
        index="city",
        columns="category",
        aggfunc="sum",
        margins=True,
        fill_value=0,
    )
    sql_q2 = sql_results[1]["data"]
    sql_grand_total = float(sql_q2["revenue"].sum())
    pivot_grand_total = float(pivot.loc["All", "All"])
    if not np.isclose(sql_grand_total, pivot_grand_total, atol=0.01):
        raise AssertionError(
            "Pandas pivot total does not match the SQL Q2 total: "
            f"{pivot_grand_total:.2f} != {sql_grand_total:.2f}"
        )

    city_summary = completed.groupby("city").agg(
        sum=("order_amount", "sum"),
        mean=("order_amount", "mean"),
        count=("order_id", "count"),
    )
    amounts = completed["order_amount"]
    q1 = float(amounts.quantile(0.25))
    median = float(amounts.median())
    q3 = float(amounts.quantile(0.75))
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr

    variables = ["order_amount", "discount_pct", "quantity", "delivery_minutes"]
    correlations = completed[variables].corr(numeric_only=True)
    correlation_pairs = [
        (left, right, float(correlations.loc[left, right]))
        for i, left in enumerate(variables)
        for right in variables[i + 1 :]
        if pd.notna(correlations.loc[left, right])
    ]
    strongest_correlation = (
        max(correlation_pairs, key=lambda pair: abs(pair[2]))
        if correlation_pairs
        else None
    )
    statistics = {
        "mean": float(amounts.mean()),
        "median": median,
        "skewness": float(amounts.skew()),
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "lower_fence": lower_fence,
        "upper_fence": upper_fence,
        "outliers_below": int((amounts < lower_fence).sum()),
        "outliers_above": int((amounts > upper_fence).sum()),
        "completed_order_count": int(len(completed)),
        "completed_revenue": float(amounts.sum()),
    }
    return {
        "pivot": pivot,
        "sql_grand_total": sql_grand_total,
        "pivot_grand_total": pivot_grand_total,
        "city_summary": city_summary,
        "statistics": statistics,
        "correlations": correlations,
        "strongest_correlation": strongest_correlation,
    }


def _print_sql_results(results: list[dict]) -> None:
    print("Seven SQL query results (actual database values)")
    for result in results:
        query_id = result["query_id"]
        frame = result["data"]
        print(f"  Q{query_id}: {len(frame)} result rows")
        if query_id == 1:
            print(f"    customers qualifying: {len(frame)}")
        elif query_id == 2:
            total = float(frame["revenue"].sum())
            highest = frame.loc[frame["revenue"].idxmax()]
            print(f"    city/category combinations: {len(frame)}")
            print(f"    completed revenue total: INR {total:,.2f}")
            print(
                "    highest combination: "
                f"{highest['city']} / {highest['category']} "
                f"(INR {highest['revenue']:,.2f})"
            )
            print(frame.to_string(index=False))
        elif query_id == 3:
            print(frame.to_string(index=False))
        elif query_id == 4:
            print(f"    customers without completed orders: {len(frame)}")
        elif query_id == 5:
            print(f"    customers above average spend: {len(frame)}")
            if not frame.empty:
                average = float(frame["mean_customer_spend"].iloc[0])
                print(f"    average customer completed spend: INR {average:,.2f}")
        elif query_id == 6:
            tie_rows = int((frame["spend_rank"] != frame["spend_row_number"]).sum())
            tops = (
                frame.sort_values(["city", "spend_row_number"])
                .groupby("city", as_index=False)
                .head(1)
            )
            print(f"    rows where RANK differs from ROW_NUMBER: {tie_rows}")
            print("    top customer in each city:")
            print(tops.to_string(index=False))
        elif query_id == 7 and not frame.empty:
            last = frame.iloc[-1]
            print(
                f"    daily rows: {len(frame)}; final cumulative revenue: "
                f"INR {last['cumulative_revenue']:,.2f}"
            )


def _print_pandas_results(analysis: dict) -> None:
    pivot = analysis["pivot"]
    stats = analysis["statistics"]
    city_summary = analysis["city_summary"]
    print("Pandas Q2 pivot table (margins=True)")
    print(pivot.to_string(float_format=lambda value: f"{value:,.2f}"))
    print(
        "Pandas/SQL grand-total cross-check: "
        f"SQL=INR {analysis['sql_grand_total']:,.2f}; "
        f"Pandas=INR {analysis['pivot_grand_total']:,.2f}; PASS"
    )
    print("Completed-order city summary (sum, mean, count)")
    print(city_summary.to_string(float_format=lambda value: f"{value:,.2f}"))

    print("Completed order_amount distribution")
    for key in (
        "completed_order_count",
        "mean",
        "median",
        "skewness",
        "q1",
        "q3",
        "iqr",
        "lower_fence",
        "upper_fence",
        "outliers_below",
        "outliers_above",
        "completed_revenue",
    ):
        value = stats[key]
        if key in {"completed_order_count", "outliers_below", "outliers_above"}:
            print(f"  {key}: {value}")
        elif key == "skewness":
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: INR {value:,.2f}")

    print("Completed-order correlations")
    print(analysis["correlations"].to_string(float_format=lambda value: f"{value:.4f}"))
    strongest = analysis["strongest_correlation"]
    if strongest:
        print(
            "  largest absolute available correlation: "
            f"{strongest[0]} vs {strongest[1]} = {strongest[2]:.4f}"
        )

    if stats["completed_order_count"]:
        interpretation = (
            f"The data describes completed retail orders across "
            f"{city_summary.shape[0]} cleaned cities and "
            f"{stats['completed_order_count']:,} completed orders. "
            f"Order amounts have mean INR {stats['mean']:,.2f}, median "
            f"INR {stats['median']:,.2f}, and skewness {stats['skewness']:.2f}, "
            f"showing a right-skewed distribution. Tukey's upper fence is "
            f"INR {stats['upper_fence']:,.2f}; {stats['outliers_above']} orders "
            f"are above it. Correlation is descriptive and does not establish "
            f"causation. Missing delivery times can make delivery correlations "
            f"unavailable and are reported by the cleaning validation."
        )
    else:
        interpretation = "No completed orders are available for EDA."
    print("EDA interpretation (under 200 words)")
    print(f"  {interpretation}")


def main() -> dict:
    results = run_sql_queries()
    if len(results) != 7:
        raise AssertionError(f"Expected seven SQL queries, found {len(results)}.")
    _print_sql_results(results)
    analysis = run_pandas_analysis(results)
    _print_pandas_results(analysis)
    return {"sql_results": results, "pandas_analysis": analysis}


if __name__ == "__main__":
    main()
