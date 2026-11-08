from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime
from typing import Any

from src.config import OUTPUTS_DIR, RAW_DIR
from src.part_d.refund_tools import calculate_refund, escalate_to_human, get_order

ASSESSMENTS_PATH = OUTPUTS_DIR / "refund_assessments.jsonl"
ORDER_ID_PATTERN = re.compile(r"\bORD-\d{6}\b", re.IGNORECASE)
FRAUD_TERMS = ("fraud", "unauthorized", "account takeover", "stolen account")


def _extract_order_id(message: str) -> str | None:
    match = ORDER_ID_PATTERN.search(message)
    return match.group(0).upper() if match else None


def _as_date(value: date | str | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _assessment(
    status: str,
    reason: str,
    *,
    refund_inr: float | None = None,
    handoff: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": status,
        "reason": reason,
        "refund_inr": refund_inr,
        "refund_executed": False,
        "notification_sent": False,
    }
    if handoff is not None:
        result["handoff"] = handoff
    return result


def evaluate_refund_request(
    order_id: str,
    customer_id: str | None,
    request_text: str = "",
    evaluation_date: date | str | None = None,
    step_count: int = 1,
) -> dict[str, Any]:
    if not isinstance(step_count, int) or isinstance(step_count, bool) or step_count < 0:
        raise ValueError("step_count must be a nonnegative integer")
    if not ORDER_ID_PATTERN.fullmatch(order_id):
        return _assessment("INVALID_ORDER_ID", "Provide a valid order identifier.")

    lowered_request = request_text.lower()
    if any(term in lowered_request for term in FRAUD_TERMS):
        handoff = escalate_to_human(
            "Potential fraud requires security review within 2 hours.",
            "security team",
        )
        handoff["response_target"] = "within 2 hours"
        return _assessment(
            "SECURITY_HANDOFF_REQUIRED",
            "Potential fraud must be reviewed by the security team.",
            handoff=handoff,
        )

    if step_count >= 6:
        handoff = escalate_to_human(
            "The support interaction reached the 6-step human-handoff limit.",
            "human support",
        )
        return _assessment(
            "HUMAN_HANDOFF_REQUIRED",
            "The support interaction reached the 6-step handoff limit.",
            handoff=handoff,
        )

    if not customer_id or not customer_id.strip():
        return _assessment(
            "CUSTOMER_VERIFICATION_REQUIRED",
            "Verify the customer before looking up or assessing this order.",
        )

    order = get_order(order_id, customer_id)
    if "error" in order:
        return _assessment(
            "ORDER_NOT_FOUND_OR_NOT_OWNED",
            "The order could not be verified for this customer.",
        )

    if order["status"] == "cancelled":
        return _assessment("DENIED_CANCELLED", "Cancelled orders are not eligible for refunds.")
    if order["status"] != "completed":
        return _assessment("DENIED_NOT_COMPLETED", "Only completed orders can be considered.")

    try:
        completed_date = date.fromisoformat(str(order["order_ts"])[:10])
        as_of = _as_date(evaluation_date)
    except (TypeError, ValueError):
        return _assessment(
            "NEEDS_REVIEW",
            "The order completion date or evaluation date is invalid.",
        )

    age_days = (as_of - completed_date).days
    if age_days < 0:
        return _assessment("NEEDS_REVIEW", "The order completion date is in the future.")
    if age_days > 7:
        return _assessment(
            "DENIED_OUTSIDE_WINDOW",
            "Refund requests must be made within 7 calendar days of completion.",
        )

    delivery_minutes = order["delivery_minutes"]
    if delivery_minutes is None:
        return _assessment(
            "NEEDS_REVIEW",
            "The database has no measured delivery time; a delay cannot be verified.",
        )
    try:
        refund = calculate_refund(order["order_amount"], delivery_minutes)["refund_inr"]
    except (TypeError, ValueError):
        return _assessment("NEEDS_REVIEW", "The stored amount or delivery time is invalid.")

    if refund == 0:
        return _assessment(
            "DENIED_NO_QUALIFYING_DELAY",
            "A measured delivery time of 45 minutes or less does not qualify.",
            refund_inr=0.0,
        )
    if refund > 1000:
        handoff = escalate_to_human(
            "Refunds above INR 1,000 require human support lead approval.",
            "human support lead",
        )
        return _assessment(
            "HUMAN_APPROVAL_REQUIRED",
            "The measured delay qualifies, but the amount requires human approval.",
            refund_inr=refund,
            handoff=handoff,
        )
    return _assessment(
        "REFUND_ELIGIBLE_NOT_EXECUTED",
        "Policy eligibility is met; no refund was issued by this assistant.",
        refund_inr=refund,
    )


def run_agent(
    user_message: str,
    scenario_id: str,
    max_iterations: int = 6,
    token_limit: int = 6000,
    time_limit_seconds: int = 10,
    customer_id: str | None = None,
    evaluation_date: date | str | None = None,
    step_count: int = 1,
    order_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(user_message, str):
        raise TypeError("user_message must be a string")
    message_order_id = _extract_order_id(user_message)
    if order_id and message_order_id and order_id.upper() != message_order_id:
        result = _assessment(
            "INVALID_ORDER_ID",
            "The supplied order identifier does not match the message.",
        )
    else:
        verified_order_id = message_order_id or order_id
        if verified_order_id is None:
            result = _assessment(
                "MISSING_ORDER_ID",
                "Provide an order identifier to continue.",
            )
        else:
            result = evaluate_refund_request(
                order_id=verified_order_id.upper(),
                customer_id=customer_id,
                request_text=user_message,
                evaluation_date=evaluation_date,
                step_count=step_count,
            )
    return {
        "scenario_id": scenario_id,
        "status": result["status"],
        "final_answer": f"{result['status']}: {result['reason']}",
        "assessment": result,
        "steps": [{"tool": "assess_refund", "observation": result}],
        "llm_calls": 0,
        "tokens_used": 0,
        "max_iterations": max_iterations,
        "token_limit": token_limit,
        "time_limit_seconds": time_limit_seconds,
    }


def main() -> list[dict[str, Any]]:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    records: list[dict[str, Any]] = []
    with (RAW_DIR / "agent_scenarios.csv").open(
        encoding="utf-8-sig", newline=""
    ) as source:
        for scenario in csv.DictReader(source):
            result = run_agent(
                scenario["user_message"],
                scenario["scenario_id"],
                evaluation_date=date.today(),
                order_id=scenario["order_id"],
            )
            records.append(
                {
                    "scenario_id": scenario["scenario_id"],
                    "status": result["status"],
                    "final_answer": result["final_answer"],
                    "refund_executed": result["assessment"]["refund_executed"],
                    "notification_sent": result["assessment"]["notification_sent"],
                }
            )

    with ASSESSMENTS_PATH.open("w", encoding="utf-8") as destination:
        for record in records:
            destination.write(json.dumps(record, sort_keys=True) + "\n")
    print(f"Part D completed: {len(records)} refund requests assessed; no refunds executed.")
    return records


if __name__ == "__main__":
    main()
