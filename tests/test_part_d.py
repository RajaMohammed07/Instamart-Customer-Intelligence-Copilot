from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import mock_llm

from src.part_d.policy_retrieval import (
    answer,
    retrieve_policy,
    validate_grounded_response,
)
from src.part_d.refund_agent import evaluate_refund_request, run_agent
from src.part_d.refund_tools import get_order


class PolicyRetrievalTests(unittest.TestCase):
    def test_normal_delivery_estimate_uses_policy_text(self) -> None:
        result = answer("What is the normal delivery estimate?")
        self.assertIn("The normal delivery estimate is 30 minutes.", result["answer"])
        self.assertIn("assignment_rules.txt", result["sources_used"])

    def test_rainy_delivery_estimate_uses_policy_text(self) -> None:
        result = answer("What is the rainy delivery estimate?")
        self.assertIn("The delivery estimate during rain is 60 minutes.", result["answer"])
        self.assertIn("assignment_rules.txt", result["sources_used"])

    def test_combined_question_returns_both_delivery_estimates(self) -> None:
        question = "What are the normal and rainy delivery estimates?"
        results = retrieve_policy(question)["results"]
        texts = [item["text"] for item in results]
        self.assertTrue(
            any("normal delivery estimate is 30 minutes" in text for text in texts)
        )
        self.assertTrue(
            any("delivery estimate during rain is 60 minutes" in text for text in texts)
        )

        result = answer(question)
        self.assertIn("The normal delivery estimate is 30 minutes.", result["answer"])
        self.assertIn("The delivery estimate during rain is 60 minutes.", result["answer"])
        self.assertEqual(result["sources_used"], ["assignment_rules.txt"])
        self.assertTrue(result["grounded"])
        self.assertFalse(
            validate_grounded_response(
                result["answer"] + "\nThe rainy estimate is 15 minutes.",
                results,
            )
        )

    def test_answer_quotes_retrieved_policy_and_cites_source(self) -> None:
        result = answer("What refund applies when delivery takes more than 45 minutes?")
        self.assertIn(
            "A completed order delivered in more than 45 minutes qualifies for a full refund.",
            result["answer"],
        )
        self.assertIn("assignment_rules.txt", result["sources_used"])
        self.assertEqual(len(result["sources_used"]), len(set(result["sources_used"])))
        self.assertTrue(result["grounded"])
        self.assertEqual(result["mock_category"], "billing")

    def test_no_match_returns_safe_fallback(self) -> None:
        result = answer("zxqv blorf")
        self.assertEqual(
            result["answer"],
            "I could not find that information in the policy documents.",
        )
        self.assertEqual(result["sources_used"], [])
        self.assertTrue(result["grounded"])

    def test_model_output_is_not_used_as_policy_answer(self) -> None:
        with patch("mock_llm.chat", return_value={"content": "not valid json"}):
            result = answer("refund for a delayed delivery")
        self.assertIn("45 minutes", result["answer"])
        self.assertIsNone(result["mock_category"])

    def test_model_receives_only_a_topic_token_not_the_question(self) -> None:
        question = "refund for ORD-123456; contact me at customer@example.com"
        with patch("mock_llm.chat", wraps=mock_llm.chat) as chat:
            answer(question)
        messages = chat.call_args.args[0]
        self.assertEqual(messages[1]["content"], "billing")
        self.assertNotIn("ORD-123456", json.dumps(messages))
        self.assertNotIn("customer@example.com", json.dumps(messages))

    def test_grounding_validator_rejects_unsupported_text(self) -> None:
        source = [{"doc": "refund_policy.txt", "text": "Refunds are allowed."}]
        self.assertTrue(
            validate_grounded_response(
                "Relevant policy text:\n- [refund_policy.txt] Refunds are allowed.",
                source,
            )
        )
        self.assertFalse(
            validate_grounded_response(
                "[refund_policy.txt] All orders receive a refund.", source
            )
        )
        self.assertFalse(
            validate_grounded_response(
                "Relevant policy text:\n- [refund_policy.txt] Refunds are allowed. "
                "All orders receive a refund.",
                source,
            )
        )


class RefundAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "refund_test.db"
        connection = sqlite3.connect(self.database)
        try:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE orders (
                        order_id TEXT PRIMARY KEY,
                        customer_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        order_amount REAL,
                        delivery_minutes REAL,
                        order_ts TEXT
                    )
                    """
                )
                connection.executemany(
                    "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        ("ORD-000001", "C0001", "completed", 128.25, 65, "2025-01-02 10:00:00"),
                        ("ORD-000002", "C0001", "completed", 1999.0, 65, "2025-01-02 10:00:00"),
                        ("ORD-000003", "C0001", "completed", 50.0, None, "2025-01-02 10:00:00"),
                        ("ORD-000004", "C0001", "cancelled", 100.0, None, "2025-01-02 10:00:00"),
                        ("ORD-000005", "C0001", "pending", 100.0, None, "2025-01-02 10:00:00"),
                    ],
                )
        finally:
            connection.close()
        self.database_patch = patch("src.part_d.refund_tools.DB_PATH", self.database)
        self.database_patch.start()
        self.addCleanup(self.database_patch.stop)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def assess(
        self,
        order_id: str,
        customer_id: str | None = "C0001",
        evaluation_date: str = "2025-01-05",
        request_text: str = "",
        step_count: int = 1,
    ) -> dict[str, Any]:
        return evaluate_refund_request(
            order_id,
            customer_id,
            request_text=request_text,
            evaluation_date=evaluation_date,
            step_count=step_count,
        )

    def test_read_only_lookup_requires_customer_ownership(self) -> None:
        self.assertEqual(
            get_order("ORD-000001", "C9999")["error"],
            "order not found or customer verification failed",
        )

    def test_missing_delivery_measurement_requires_review(self) -> None:
        result = self.assess("ORD-000003")
        self.assertEqual(result["status"], "NEEDS_REVIEW")
        self.assertFalse(result["refund_executed"])

    def test_eligible_refund_is_not_executed(self) -> None:
        result = self.assess("ORD-000001")
        self.assertEqual(result["status"], "REFUND_ELIGIBLE_NOT_EXECUTED")
        self.assertEqual(result["refund_inr"], 128.25)
        self.assertFalse(result["refund_executed"])
        self.assertFalse(result["notification_sent"])

    def test_large_refund_requires_human_approval(self) -> None:
        result = self.assess("ORD-000002")
        self.assertEqual(result["status"], "HUMAN_APPROVAL_REQUIRED")
        self.assertEqual(result["handoff"]["target"], "human support lead")  # type: ignore[index]
        self.assertFalse(result["handoff"]["external_action_taken"])  # type: ignore[index]

    def test_cancelled_and_pending_orders_are_not_refundable(self) -> None:
        self.assertEqual(self.assess("ORD-000004")["status"], "DENIED_CANCELLED")
        self.assertEqual(self.assess("ORD-000005")["status"], "DENIED_NOT_COMPLETED")

    def test_seven_day_window_is_enforced(self) -> None:
        result = self.assess("ORD-000001", evaluation_date="2025-01-10")
        self.assertEqual(result["status"], "DENIED_OUTSIDE_WINDOW")

    def test_fraud_and_six_steps_create_handoff_without_sending_it(self) -> None:
        fraud = self.assess("ORD-000001", request_text="I suspect fraud")
        self.assertEqual(fraud["status"], "SECURITY_HANDOFF_REQUIRED")
        self.assertEqual(fraud["handoff"]["response_target"], "within 2 hours")  # type: ignore[index]
        steps = self.assess("ORD-000001", step_count=6)
        self.assertEqual(steps["status"], "HUMAN_HANDOFF_REQUIRED")
        self.assertFalse(steps["notification_sent"])

    def test_missing_order_id_does_not_fall_back_to_another_order(self) -> None:
        result = run_agent("Please help with a refund.", "S1")
        self.assertEqual(result["status"], "MISSING_ORDER_ID")
        self.assertFalse(result["assessment"]["refund_executed"])

    def test_missing_customer_identity_requires_verification(self) -> None:
        result = run_agent("Refund for ORD-000001", "S1")
        self.assertEqual(result["status"], "CUSTOMER_VERIFICATION_REQUIRED")

    def test_scenario_order_id_still_requires_customer_verification(self) -> None:
        result = run_agent(
            "Please help with a refund.",
            "S1",
            order_id="ORD-000001",
        )
        self.assertEqual(result["status"], "CUSTOMER_VERIFICATION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
