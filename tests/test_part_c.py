from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import pandas as pd

from src.part_c.classifier import classify_ticket
from src.part_c.privacy import count_redactions, redact_pii
from src.part_c.ticket_routing import (
    audit_ticket_data,
    build_enrichment_maps,
    enrich_customer,
    route_ticket,
)


class PrivacyTests(unittest.TestCase):
    def test_masks_email_indian_mobile_and_order_id(self) -> None:
        message = "Email raja@example.com, phone 9876543210, order ORD-123456."
        masked = redact_pii(message)
        self.assertIn("[EMAIL]", masked)
        self.assertIn("[PHONE]", masked)
        self.assertIn("[ORDER_ID]", masked)
        self.assertEqual(count_redactions(masked), {"emails": 0, "phones": 0, "order_ids": 0})

    def test_masks_multiple_values_in_one_message(self) -> None:
        message = "a@example.com and b@example.org called +91 9876543210."
        masked = redact_pii(message)
        self.assertEqual(masked.count("[EMAIL]"), 2)
        self.assertEqual(masked.count("[PHONE]"), 1)

    def test_masks_international_phone(self) -> None:
        self.assertIn("[PHONE]", redact_pii("Call me at +1 (202) 555-0101."))

    def test_handles_empty_and_none(self) -> None:
        self.assertEqual(redact_pii(""), "")
        self.assertEqual(redact_pii(None), "")
        self.assertEqual(count_redactions(""), {"emails": 0, "phones": 0, "order_ids": 0})

    def test_does_not_mask_ordinary_numbers(self) -> None:
        message = "The total is INR 1,999 and I ordered 123456 items."
        self.assertEqual(redact_pii(message), message)


class TicketAuditTests(unittest.TestCase):
    def test_reports_invalid_rows_without_dropping_them(self) -> None:
        repeated = {
            "ticket_id": "T2",
            "customer_id": "UNKNOWN",
            "text": "long " * 401,
            "true_category": "other",
            "created_at": "",
        }
        tickets = pd.DataFrame(
            [
                {
                    "ticket_id": "",
                    "customer_id": "C1",
                    "text": "",
                    "true_category": "billing",
                    "created_at": "2025-01-01",
                },
                repeated,
                repeated,
            ]
        )
        report = audit_ticket_data(tickets, {"C1"})
        self.assertEqual(report["total_records"], 3)
        self.assertEqual(report["exact_duplicate_rows"], 1)
        self.assertEqual(report["duplicate_ticket_id_rows"], 1)
        self.assertEqual(report["missing_ticket_ids"], 1)
        self.assertEqual(report["unknown_customer_ids"], 2)
        self.assertEqual(report["empty_messages"], 1)
        self.assertEqual(report["long_messages_over_400_tokens"], 2)
        self.assertEqual(report["missing_or_invalid_timestamps"], 2)
        self.assertEqual(report["invalid_true_categories"], 2)
        self.assertEqual(report["cleaning_decisions"]["rows_dropped"], 0)


class ClassificationTests(unittest.TestCase):
    @patch("src.part_c.classifier.mock_llm.chat")
    def test_valid_category_and_only_masked_text_is_sent(self, chat) -> None:
        chat.return_value = {
            "content": '{"category":"billing","reason":"Payment issue."}'
        }
        result = classify_ticket("Email me at user@example.com, phone 9876543210.")
        sent = chat.call_args.args[0][0]["content"]
        self.assertEqual(result["status"], "classified_json")
        self.assertNotIn("user@example.com", sent)
        self.assertNotIn("9876543210", sent)
        self.assertIn("[EMAIL]", sent)
        self.assertIn("[PHONE]", sent)

    @patch("src.part_c.classifier.mock_llm.chat")
    def test_invalid_category_is_not_fabricated(self, chat) -> None:
        chat.return_value = {"content": '{"category":"other","reason":"Unknown"}'}
        result = classify_ticket("My payment is missing.")
        self.assertEqual(result["status"], "flagged_invalid_output")

    @patch("src.part_c.classifier.mock_llm.chat")
    def test_clear_unauthorized_account_signal_routes_as_fraud(self, chat) -> None:
        chat.return_value = {
            "content": '{"category":"billing","reason":"Default safe classification."}'
        }
        result = classify_ticket("Someone used my account to make a purchase.")
        payload = json.loads(result["text"])
        self.assertEqual(payload["category"], "fraud")
        self.assertEqual(result["status"], "classified_json")

    @patch("src.part_c.classifier.mock_llm.chat")
    def test_empty_and_long_messages_are_not_sent(self, chat) -> None:
        self.assertEqual(classify_ticket(" ")["status"], "skipped_empty")
        self.assertEqual(classify_ticket("word " * 401)["status"], "flagged_long")
        chat.assert_not_called()

    @patch("src.part_c.classifier.mock_llm.chat", side_effect=ValueError("offline"))
    def test_unexpected_mock_exception_is_visible(self, chat) -> None:
        with self.assertRaisesRegex(ValueError, "offline"):
            classify_ticket("My app has an error.")
        chat.assert_called_once()


class EnrichmentTests(unittest.TestCase):
    def setUp(self) -> None:
        segments = pd.DataFrame(
            [
                {"customer_id": "C_HIGH", "segment_name": "High-Value Regulars", "is_premium": "1"},
                {"customer_id": "C_RISK", "segment_name": "At-Risk Shoppers", "is_premium": "0"},
            ]
        )
        retention = pd.DataFrame(
            [{"customer_id": "C_HIGH", "lapse_probability": "0.72"}]
        )
        self.segment_map, self.lapse_map, self.invalid = build_enrichment_maps(
            segments, retention
        )

    def test_premium_customer_with_prediction(self) -> None:
        result = enrich_customer("C_HIGH", self.segment_map, self.lapse_map)
        self.assertEqual(result["customer_segment"], "High-Value Regulars")
        self.assertEqual(result["premium_status"], "premium")
        self.assertEqual(result["lapse_prediction"], "lapsed")
        self.assertEqual(result["lapse_probability"], 0.72)
        self.assertEqual(result["enrichment_status"], "matched")

    def test_at_risk_customer_without_prediction_stays_unknown(self) -> None:
        result = enrich_customer("C_RISK", self.segment_map, self.lapse_map)
        self.assertEqual(result["customer_segment"], "At-Risk Shoppers")
        self.assertEqual(result["premium_status"], "not_premium")
        self.assertIsNone(result["lapse_prediction"])
        self.assertIsNone(result["lapse_probability"])

    def test_unknown_and_missing_customer_ids(self) -> None:
        unknown = enrich_customer("C_UNKNOWN", self.segment_map, self.lapse_map)
        missing = enrich_customer("", self.segment_map, self.lapse_map)
        self.assertEqual(unknown["enrichment_status"], "unknown_customer_id")
        self.assertEqual(missing["enrichment_status"], "missing_customer_id")
        self.assertIsNone(unknown["lapse_prediction"])
        self.assertIsNone(missing["lapse_prediction"])


class RoutingTests(unittest.TestCase):
    def test_category_to_team_routing(self) -> None:
        expected = {
            "billing": "Billing Support",
            "delivery": "Delivery Support",
            "technical": "Technical Support",
            "fraud": "Fraud/Security Team",
        }
        for category, team in expected.items():
            with self.subTest(category=category):
                result = route_ticket(category, "classified_json", "matched")
                self.assertEqual(result["assigned_team"], team)
                self.assertEqual(result["priority"], "NORMAL")

    def test_customer_context_does_not_override_category(self) -> None:
        premium = route_ticket(
            "billing",
            "classified_json",
            "matched",
            "High-Value Regulars",
            "premium",
        )
        at_risk = route_ticket(
            "delivery",
            "classified_json",
            "matched",
            "At-Risk Shoppers",
            "not_premium",
            "lapsed",
        )
        conflict = route_ticket(
            "fraud",
            "classified_json",
            "matched",
            "High-Value Regulars",
            "premium",
            "lapsed",
        )
        self.assertEqual(premium["assigned_team"], "Billing Support")
        self.assertEqual(at_risk["assigned_team"], "Delivery Support")
        self.assertEqual(conflict["assigned_team"], "Fraud/Security Team")
        self.assertEqual(conflict["priority"], "NORMAL")
        self.assertIn("informational only", conflict["routing_reason"])

    def test_missing_customer_does_not_invent_enrichment_or_category(self) -> None:
        category_route = route_ticket("technical", "classified_json", "missing_customer_id")
        review_route = route_ticket(None, "flagged_invalid_output", "missing_customer_id")
        self.assertEqual(category_route["assigned_team"], "Technical Support")
        self.assertIn("enrichment is unavailable", category_route["routing_reason"])
        self.assertEqual(review_route["assigned_team"], "Human Support Lead")


if __name__ == "__main__":
    unittest.main()
