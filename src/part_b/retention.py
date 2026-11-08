from __future__ import annotations

import numpy as np
import pandas as pd


def generate_retention_list(
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    customer_ids=None,
    premium_customer_ids=None,
) -> pd.DataFrame:
    if customer_ids is None:
        if "customer_id" not in X_test.columns:
            raise ValueError("Actual customer_ids are required to build a retention list.")
        customer_ids = X_test["customer_id"].to_numpy()
        X_test = X_test.drop(columns="customer_id")
    if len(customer_ids) != len(X_test) or len(y_test) != len(X_test):
        raise ValueError("Customer IDs, test features, and test labels must align.")

    lapse_class_index = int(np.flatnonzero(model.classes_ == 1)[0])
    results = pd.DataFrame(
        {
            "customer_id": np.asarray(customer_ids),
            "lapse_probability": model.predict_proba(X_test)[:, lapse_class_index],
            "actually_lapsed": y_test.to_numpy(),
        },
        index=X_test.index,
    )
    if premium_customer_ids is not None:
        results = results.loc[results["customer_id"].isin(premium_customer_ids)]
    return results.sort_values("lapse_probability", ascending=False).head(10)
