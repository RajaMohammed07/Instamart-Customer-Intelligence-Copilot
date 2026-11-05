from __future__ import annotations

import pandas as pd


def validate_checkpoints(customers: pd.DataFrame, orders: pd.DataFrame):
    assert customers['city'].isin(['Chennai', 'Mumbai', 'Bengaluru', 'Delhi', 'Hyderabad', 'Pune']).all()
    assert (customers['gender'].isin(['male', 'female', 'unknown'])).all()
    assert customers['age'].between(18, 60).all()
    assert customers['age'].notna().all()
    assert len(orders) == 12309
    assert orders['status'].isin(['completed', 'cancelled']).all()
    assert orders['order_amount'].notna().all()
    assert orders['delivery_minutes'].notna().sum() == 11110
    assert (orders['status'] == 'cancelled').sum() == 1199
    print('ALL CHECKPOINTS PASSED')
