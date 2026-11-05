from __future__ import annotations

import pandas as pd


def generate_retention_list(model, X_test, y_test):
    pred = model.predict_proba(X_test)[:, 1]
    df = X_test.copy()
    df['customer_id'] = df.index
    df['lapse_probability'] = pred
    df['actually_lapsed'] = y_test.to_numpy()
    return df[['customer_id', 'lapse_probability', 'actually_lapsed']].sort_values('lapse_probability', ascending=False).head(10)
