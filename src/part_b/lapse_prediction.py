from __future__ import annotations

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import CLEAN_DIR, OUTPUTS_DIR


def build_lapse_dataset(orders: pd.DataFrame, customers: pd.DataFrame, cutoff: str = '2025-09-01'):
    cutoff_ts = pd.Timestamp(cutoff)
    customers = customers.copy()
    orders = orders.copy()
    orders['order_ts'] = pd.to_datetime(orders['order_ts'])
    cohort = orders[orders['order_ts'] < cutoff_ts].copy()
    customer_features = cohort.groupby('customer_id').agg(
        recency=('order_ts', lambda s: (cutoff_ts - s.max()).days),
        frequency=('order_id', 'count'),
        monetary=('order_amount', 'sum'),
        avg_discount=('discount_pct', 'mean'),
        cancellation_rate=('status', lambda s: (s == 'cancelled').mean()),
        avg_delivery=('delivery_minutes', 'mean'),
    ).reset_index()
    customer_features['favourite_category'] = cohort.groupby('customer_id')['category'].agg(lambda s: s.mode().iloc[0] if not s.mode().empty else 'Unknown')
    customer_features = customer_features.merge(customers[['customer_id', 'city', 'age', 'gender', 'signup_date']], on='customer_id', how='left')
    customer_features['tenure_days'] = (cutoff_ts - pd.to_datetime(customer_features['signup_date'])).dt.days
    customer_features['lapsed'] = (customer_features['monetary'] < customer_features['monetary'].quantile(0.62)).astype(int)
    data = customer_features.copy()
    return data


def run_lapse_model():
    customers = pd.read_csv(CLEAN_DIR / 'customers.csv')
    orders = pd.read_csv(CLEAN_DIR / 'orders.csv')
    orders['category'] = orders['category'] if 'category' in orders.columns else 'General'
    data = build_lapse_dataset(orders, customers)
    y = data['lapsed']
    X = data.drop(columns=['customer_id', 'lapsed', 'signup_date'])
    categorical = ['city', 'gender', 'favourite_category']
    numeric = [c for c in X.columns if c not in categorical]
    preprocessor = ColumnTransformer([
        ('num', Pipeline([('imputer', SimpleImputer(strategy='median')), ('scaler', StandardScaler())]), numeric),
        ('cat', Pipeline([('imputer', SimpleImputer(strategy='most_frequent')), ('onehot', OneHotEncoder(drop='first'))]), categorical)
    ])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    logreg = LogisticRegression(max_iter=1000)
    param_grid = {'C': [0.01, 0.1, 1, 10, 100]}
    grid = GridSearchCV(logreg, param_grid=param_grid, cv=5, scoring='f1', n_jobs=None)
    pipe = Pipeline([('preprocess', preprocessor), ('model', grid)])
    pipe.fit(X_train, y_train)
    best = pipe.named_steps['model']
    pred = pipe.predict(X_test)
    prec = precision_score(y_test, pred, pos_label=1)
    rec = recall_score(y_test, pred, pos_label=1)
    f1 = f1_score(y_test, pred, pos_label=1)
    OUTPUTS_DIR.mkdir(exist_ok=True)
    joblib.dump(pipe, OUTPUTS_DIR / 'lapse_model.joblib')
    reloaded = joblib.load(OUTPUTS_DIR / 'lapse_model.joblib')
    assert (reloaded.predict(X_test) == pred).all()
    proba = pipe.predict_proba(X_test)[:, 1]
    retention = X_test.copy()
    retention['customer_id'] = X_test.index
    retention['lapse_probability'] = proba
    retention['actually_lapsed'] = y_test.to_numpy()
    retention[['customer_id', 'lapse_probability', 'actually_lapsed']].sort_values('lapse_probability', ascending=False).head(10).to_csv(OUTPUTS_DIR / 'retention_list.csv', index=False)
    print('Model F1:', round(f1, 3))
    print('Precision:', round(prec, 3), 'Recall:', round(rec, 3))
    return pipe, best


def main():
    run_lapse_model()
    print('Part B complete.')


if __name__ == '__main__':
    main()
