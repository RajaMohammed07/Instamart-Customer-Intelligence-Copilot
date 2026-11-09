from __future__ import annotations

import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.config import OUTPUTS_DIR
from src.part_b.customer_segmentation import _name_segments
from src.part_b.retention import generate_retention_list
from src.part_b.rfm_analysis import compute_rfm, identify_premium_customers


class RFMAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.customers = pd.DataFrame(
            {"customer_id": [f"C{i:04d}" for i in range(1, 6)]}
        )
        self.orders = pd.DataFrame(
            [
                {"order_id": "O1", "customer_id": "C0001", "status": "completed", "order_amount": 100.0, "order_ts": "2025-09-20 10:00:00"},
                {"order_id": "O2", "customer_id": "C0001", "status": "completed", "order_amount": 150.0, "order_ts": "2025-09-25 10:00:00"},
                {"order_id": "O3", "customer_id": "C0002", "status": "completed", "order_amount": 500.0, "order_ts": "2025-08-01 10:00:00"},
                {"order_id": "O4", "customer_id": "C0002", "status": "cancelled", "order_amount": 300.0, "order_ts": "2025-09-28 10:00:00"},
                {"order_id": "O5", "customer_id": "C0003", "status": "pending", "order_amount": 200.0, "order_ts": "2025-09-29 10:00:00"},
                {"order_id": "O6", "customer_id": "C0004", "status": "completed", "order_amount": 50.0, "order_ts": "2025-09-30 10:00:00"},
                # C0005 has no orders
            ]
        )

    def test_compute_rfm_metrics(self) -> None:
        rfm = compute_rfm(self.orders, self.customers, snapshot="2025-10-01")
        self.assertEqual(len(rfm), 5)
        # C0001: 2 completed orders, max date 2025-09-25 10:00:00 (5 days before Oct 1), sum = 250
        c1 = rfm.loc[rfm["customer_id"] == "C0001"].iloc[0]
        self.assertEqual(c1["frequency"], 2)
        self.assertAlmostEqual(c1["monetary"], 250.0)
        self.assertEqual(c1["recency"], 5)

        # C0002: 1 completed order (cancelled order excluded), sum = 500
        c2 = rfm.loc[rfm["customer_id"] == "C0002"].iloc[0]
        self.assertEqual(c2["frequency"], 1)
        self.assertAlmostEqual(c2["monetary"], 500.0)

        # C0003: pending order only -> frequency 0, monetary 0
        c3 = rfm.loc[rfm["customer_id"] == "C0003"].iloc[0]
        self.assertEqual(c3["frequency"], 0)
        self.assertAlmostEqual(c3["monetary"], 0.0)

        # C0005: no orders -> frequency 0, monetary 0
        c5 = rfm.loc[rfm["customer_id"] == "C0005"].iloc[0]
        self.assertEqual(c5["frequency"], 0)
        self.assertAlmostEqual(c5["monetary"], 0.0)

    def test_premium_customer_rule(self) -> None:
        rfm = pd.DataFrame(
            {
                "customer_id": [f"C{i:02d}" for i in range(1, 11)],
                "recency": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
                "frequency": [10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
                "monetary": [1000, 900, 800, 700, 600, 500, 400, 300, 200, 100],
            }
        )
        premium = identify_premium_customers(rfm)
        # Top 20% monetary = C01 (1000), C02 (900). Both have high freq and low recency
        self.assertTrue(premium.iloc[0])
        self.assertTrue(premium.iloc[1])
        # Bottom customers should not be premium
        self.assertFalse(premium.iloc[-1])


class SegmentationNamingTests(unittest.TestCase):
    def test_name_segments_assigns_valid_business_names(self) -> None:
        mock_rfm = pd.DataFrame(
            {
                "segment_id": [0, 0, 1, 1, 2, 2],
                "recency": [10, 12, 80, 85, 30, 35],
                "frequency": [15, 14, 2, 1, 8, 7],
                "monetary": [5000, 4800, 500, 450, 2000, 1900],
            }
        )
        names = _name_segments(mock_rfm)
        self.assertIn("High-Value Regulars", names.values())
        self.assertIn("At-Risk Shoppers", names.values())
        self.assertIn(names[0], ["High-Value Regulars"])


class PartBModelArtifactTests(unittest.TestCase):
    def test_model_artifacts_load_and_predict(self) -> None:
        model_path = OUTPUTS_DIR / "lapse_model.joblib"
        forest_path = OUTPUTS_DIR / "lapse_forest_model.joblib"
        oversampled_path = OUTPUTS_DIR / "lapse_oversampled_logistic_model.joblib"

        self.assertTrue(model_path.exists())
        self.assertTrue(forest_path.exists())
        self.assertTrue(oversampled_path.exists())

        model = joblib.load(model_path)
        self.assertTrue(hasattr(model, "predict"))
        self.assertTrue(hasattr(model, "predict_proba"))
        np.testing.assert_array_equal(model.classes_, [0, 1])

    def test_test_predictions_and_retention_outputs(self) -> None:
        preds_path = OUTPUTS_DIR / "lapse_test_predictions.csv"
        retention_path = OUTPUTS_DIR / "retention_list.csv"

        self.assertTrue(preds_path.exists())
        self.assertTrue(retention_path.exists())

        preds = pd.read_csv(preds_path)
        self.assertEqual(len(preds), 240)
        self.assertIn("actual_lapsed", preds.columns)
        self.assertIn("oversampled_logistic_prediction", preds.columns)

        retention = pd.read_csv(retention_path)
        self.assertEqual(len(retention), 10)
        self.assertIn("customer_id", retention.columns)
        self.assertIn("lapse_probability", retention.columns)
        # Check sorted descending
        probs = retention["lapse_probability"].tolist()
        self.assertEqual(probs, sorted(probs, reverse=True))


if __name__ == "__main__":
    unittest.main()
