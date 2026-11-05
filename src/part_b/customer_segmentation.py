from __future__ import annotations

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from src.config import CLEAN_DIR, OUTPUTS_DIR
from src.part_b.rfm_analysis import compute_rfm


def run_kmeans_and_segments(orders: pd.DataFrame, customers: pd.DataFrame):
    rfm = compute_rfm(orders, customers)
    scaler = StandardScaler()
    X = scaler.fit_transform(rfm[['recency', 'frequency', 'monetary']])
    results = []
    for k in range(2, 9):
        km = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = km.fit_predict(X)
        results.append({
            'k': k,
            'inertia': float(km.inertia_),
            'silhouette': float(silhouette_score(X, labels)),
        })
    final_k = 4
    km = KMeans(n_clusters=final_k, n_init=10, random_state=42)
    labels = km.fit_predict(X)
    rfm['segment_id'] = labels
    segment_names = {
        0: 'Value Seekers',
        1: 'Loyal Shoppers',
        2: 'At-Risk',
        3: 'Premium'
    }
    rfm['segment_name'] = rfm['segment_id'].map(segment_names)
    rfm['is_premium'] = rfm['segment_name'].eq('Premium').astype(int)
    pca = PCA(n_components=2)
    components = pca.fit_transform(X)
    explained = pca.explained_variance_ratio_
    out = rfm[['customer_id', 'recency', 'frequency', 'monetary', 'segment_id', 'segment_name', 'is_premium']].copy()
    OUTPUTS_DIR.mkdir(exist_ok=True)
    out.to_csv(OUTPUTS_DIR / 'customer_segments.csv', index=False)
    return rfm, results, explained


def main():
    customers = pd.read_csv(CLEAN_DIR / 'customers.csv')
    orders = pd.read_csv(CLEAN_DIR / 'orders.csv')
    rfm, results, explained = run_kmeans_and_segments(orders, customers)
    print('Selected K=4 for segmentation.')
    print('PCA explained variance:', explained)
    return rfm, results


if __name__ == '__main__':
    main()
