from __future__ import annotations

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from src.config import OUTPUTS_DIR
from src.part_b.lapse_prediction import run_lapse_model
from src.part_b.rfm_analysis import (
    compute_rfm,
    identify_premium_customers,
    load_part_b_data,
    rfm_summary,
)


RFM_FEATURES = ["recency", "frequency", "monetary"]
PREMIUM_RULE = (
    "monetary at or above the 80th percentile, frequency at or above its median, "
    "and recency at or below its median"
)
SEGMENT_ACTIONS = {
    "High-Value Regulars": "Reward loyalty and protect with personalized service.",
    "At-Risk Shoppers": "Use a timely win-back offer and investigate recent inactivity.",
    "Steady Shoppers": "Encourage repeat orders with relevant cross-sell recommendations.",
    "Engaged Shoppers": "Maintain engagement with relevant personalized offers.",
    "No Completed Orders": "Investigate the absence of completed purchase history.",
}


def _name_segments(rfm: pd.DataFrame) -> dict[int, str]:
    profiles = rfm.groupby("segment_id")[RFM_FEATURES].mean()
    value_score = (
        profiles["monetary"].rank(pct=True)
        + profiles["frequency"].rank(pct=True)
        - profiles["recency"].rank(pct=True)
    )
    high_value_id = int(value_score.idxmax())
    names = {high_value_id: "High-Value Regulars"}
    if len(profiles) > 1:
        remaining = profiles.drop(index=high_value_id)
        at_risk_id = int(remaining["recency"].idxmax())
        names[at_risk_id] = "At-Risk Shoppers"
    for cluster_id in profiles.index:
        cluster_id = int(cluster_id)
        if cluster_id not in names:
            names[cluster_id] = "Steady Shoppers" if len(names) == 2 else "Engaged Shoppers"
    return names


def run_kmeans_and_segments(
    orders: pd.DataFrame, customers: pd.DataFrame
) -> tuple[pd.DataFrame, list[dict], pd.Series, int]:
    rfm = compute_rfm(orders, customers)
    eligible = rfm.loc[rfm["frequency"].gt(0)].copy()
    if len(eligible) < 8:
        raise ValueError("At least eight customers with completed orders are required.")

    scaler = StandardScaler()
    X = scaler.fit_transform(eligible[RFM_FEATURES])
    results = []
    for k in range(2, 9):
        model = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = model.fit_predict(X)
        results.append(
            {
                "k": k,
                "inertia": float(model.inertia_),
                "silhouette": float(silhouette_score(X, labels)),
            }
        )
    selected_k = max(results, key=lambda result: result["silhouette"])["k"]
    model = KMeans(n_clusters=selected_k, n_init=10, random_state=42)
    eligible["segment_id"] = model.fit_predict(X)
    name_map = _name_segments(eligible)
    eligible["segment_name"] = eligible["segment_id"].map(name_map)

    rfm = rfm.merge(
        eligible[["customer_id", "segment_id", "segment_name"]],
        on="customer_id",
        how="left",
        validate="one_to_one",
    )
    no_history = rfm["frequency"].eq(0)
    rfm.loc[no_history, "segment_id"] = -1
    rfm.loc[no_history, "segment_name"] = "No Completed Orders"
    rfm["segment_id"] = rfm["segment_id"].astype(int)
    rfm["is_premium"] = identify_premium_customers(rfm).astype(int)
    rfm.loc[no_history, "is_premium"] = 0

    pca = PCA(n_components=2)
    pca.fit(X)
    explained = pd.Series(
        pca.explained_variance_ratio_,
        index=["PC1", "PC2"],
        name="explained_variance_ratio",
    )
    profiles = rfm.groupby(
        ["segment_id", "segment_name"], as_index=False, dropna=False
    ).agg(
        customers=("customer_id", "count"),
        recency=("recency", "mean"),
        frequency=("frequency", "mean"),
        monetary=("monetary", "mean"),
        premium_customers=("is_premium", "sum"),
    )
    profiles["business_action"] = profiles["segment_name"].map(SEGMENT_ACTIONS)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    rfm[
        [
            "customer_id",
            "recency",
            "frequency",
            "monetary",
            "segment_id",
            "segment_name",
            "is_premium",
        ]
    ].to_csv(OUTPUTS_DIR / "customer_segments.csv", index=False)
    rfm.to_csv(OUTPUTS_DIR / "rfm_analysis.csv", index=False)
    pd.DataFrame(results).to_csv(OUTPUTS_DIR / "rfm_kmeans_metrics.csv", index=False)
    profiles.to_csv(OUTPUTS_DIR / "customer_segment_profiles.csv", index=False)
    explained.rename_axis("component").reset_index().to_csv(
        OUTPUTS_DIR / "rfm_pca_explained_variance.csv", index=False
    )
    return rfm, results, explained, selected_k


def main() -> None:
    orders, customers = load_part_b_data()
    rfm, results, explained, selected_k = run_kmeans_and_segments(orders, customers)
    print("RFM snapshot: 2025-10-01 (completed orders only)")
    print("RFM summary:", rfm_summary(rfm))
    print("Customers with no completed orders:", int(rfm["frequency"].eq(0).sum()))
    print("\nK-means comparison (standardized RFM, n_init=10, random_state=42):")
    print(
        pd.DataFrame(results).to_string(
            index=False, float_format=lambda value: f"{value:.4f}"
        )
    )
    print(
        f"\nSelected K={selected_k}: highest observed silhouette among K=2..8; "
        "segment profiles and actions provide the business interpretation. "
        "Inertia is reported but is not used alone to choose K."
    )
    print(f"PCA explained variance ratios: {explained.to_dict()}")
    print(f"PCA total explained variance: {explained.sum():.4f}")
    print(f"Premium rule: {PREMIUM_RULE}.")
    profiles = pd.read_csv(OUTPUTS_DIR / "customer_segment_profiles.csv")
    print("Segment profiles and actions:")
    print(profiles.to_string(index=False, float_format=lambda value: f"{value:.2f}"))
    print(f"Saved Part B segmentation outputs in {OUTPUTS_DIR}.")

    model_result = run_lapse_model(orders=orders, customers=customers, segments=rfm)
    if model_result is None:
        print(
            "\nPart B segmentation completed; lapse-model training was skipped "
            "because the observed cohort does not contain both outcome classes."
        )
    return None


if __name__ == "__main__":
    main()
