from __future__ import annotations

import hashlib
import sqlite3
import unittest
from pathlib import Path

import pandas as pd

from src.config import CLEAN_DIR, DB_PATH, OUTPUTS_DIR, POLICY_DIR, RAW_DIR
from src.part_c.privacy import redact_pii
from src.part_c.ticket_routing import build_enrichment_maps, enrich_customer, route_ticket
from src.part_d.policy_retrieval import retrieve_policy
from src.part_d.refund_tools import get_order


class DatabaseAndFoundationIntegrationTests(unittest.TestCase):
    def test_database_integrity_and_table_counts(self) -> None:
        self.assertTrue(DB_PATH.exists(), f"Database missing at {DB_PATH}")
        with sqlite3.connect(DB_PATH) as conn:
            integrity = conn.execute("PRAGMA integrity_check;").fetchall()
            self.assertEqual(integrity, [("ok",)])

            c_count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
            p_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            o_count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            completed_count = conn.execute(
                "SELECT COUNT(*) FROM orders WHERE status = 'completed'"
            ).fetchone()[0]

            self.assertEqual(c_count, 1200)
            self.assertEqual(p_count, 40)
            self.assertEqual(o_count, 12309)
            self.assertEqual(completed_count, 11430)


class CustomerSegmentationToTriageIntegrationTests(unittest.TestCase):
    def test_segmentation_enriches_support_tickets(self) -> None:
        segments_path = OUTPUTS_DIR / "customer_segments.csv"
        retention_path = OUTPUTS_DIR / "retention_list.csv"
        self.assertTrue(segments_path.exists())
        self.assertTrue(retention_path.exists())

        segments_df = pd.read_csv(segments_path)
        retention_df = pd.read_csv(retention_path)

        segment_map, lapse_map, invalid_count = build_enrichment_maps(
            segments_df, retention_df
        )
        self.assertEqual(len(segment_map), 1200)

        # Check enrichment on known customer
        sample_customer_id = next(iter(segment_map.keys()))
        enrichment = enrich_customer(sample_customer_id, segment_map, lapse_map)
        self.assertIn("customer_segment", enrichment)
        self.assertIn("premium_status", enrichment)
        self.assertIn("lapse_prediction", enrichment)
        self.assertEqual(
            enrichment["customer_segment"],
            segment_map[sample_customer_id]["customer_segment"],
        )


class PolicyRetrievalAndRefundIntegrationTests(unittest.TestCase):
    def test_read_only_order_verification_against_live_database(self) -> None:
        with sqlite3.connect(DB_PATH) as conn:
            sample_order = conn.execute(
                "SELECT order_id, customer_id, order_amount FROM orders WHERE status = 'completed' LIMIT 1"
            ).fetchone()

        order_id, customer_id, amount = sample_order
        # Correct owner lookup
        order_info = get_order(order_id, customer_id)
        self.assertNotIn("error", order_info)
        self.assertEqual(order_info["order_id"], order_id)
        self.assertEqual(order_info["status"], "completed")

        # Wrong owner lookup must be rejected
        wrong_owner = get_order(order_id, "NONEXISTENT_CUST")
        self.assertIn("error", wrong_owner)

    def test_policy_retrieval_integration(self) -> None:
        # Verify policy retrieval answers with grounded sources
        from src.part_d.policy_retrieval import answer
        result = answer("What is the refund window for delivery delays?")
        self.assertTrue(result["grounded"])
        self.assertTrue(any("refund_policy.txt" in src for src in result["sources_used"]))


class ArchiveAndBaselineIntegrityIntegrationTests(unittest.TestCase):
    def test_archive_part_b_hash_parity(self) -> None:
        archive_dir = Path("archive/part_b_final")
        manifest_file = archive_dir / "SHA256SUMS.txt"
        self.assertTrue(manifest_file.exists())

        with open(manifest_file, "r", encoding="utf-8") as f:
            lines = f.read().strip().split("\n")[1:]

        for line in lines:
            expected_hash, expected_size, rel_path = line.split("\t")
            file_path = archive_dir / rel_path
            self.assertTrue(file_path.exists(), f"Missing archive file: {rel_path}")
            self.assertEqual(file_path.stat().st_size, int(expected_size))
            actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
            self.assertEqual(actual_hash, expected_hash, f"Hash mismatch for {rel_path}")


if __name__ == "__main__":
    unittest.main()
