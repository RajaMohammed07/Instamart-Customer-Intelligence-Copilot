from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import mock_llm
import pandas as pd

from src.config import OUTPUTS_DIR, RAW_DIR
from src.part_c.classifier import ALLOWED, MAX_INPUT_TOKENS, classify_ticket
from src.part_c.privacy import count_redactions, redact_pii

TOKEN_BUDGET = 100000
TICKET_COLUMNS = {"ticket_id", "customer_id", "text", "true_category", "created_at"}
SEGMENT_COLUMNS = {"customer_id", "segment_name", "is_premium"}
RETENTION_COLUMNS = {"customer_id", "lapse_probability"}
CATEGORY_TEAMS = {
    "billing": "Billing Support",
    "delivery": "Delivery Support",
    "technical": "Technical Support",
    "fraud": "Fraud/Security Team",
}


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _require_columns(frame: pd.DataFrame, required: set[str], source: str) -> None:
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"{source} is missing required columns: {missing}")


def audit_ticket_data(
    tickets: pd.DataFrame, known_customer_ids: set[str]
) -> dict[str, Any]:
    _require_columns(tickets, TICKET_COLUMNS, "Ticket data")
    ticket_ids = tickets["ticket_id"].astype(str).str.strip()
    customer_ids = tickets["customer_id"].astype(str).str.strip()
    messages = tickets["text"].fillna("").astype(str)
    categories = tickets["true_category"].fillna("").astype(str).str.strip().str.lower()
    timestamps = pd.to_datetime(
        tickets["created_at"].replace("", pd.NA), errors="coerce"
    )
    category_counts = categories.replace("", "missing").value_counts().to_dict()
    invalid_categories = ~categories.isin(ALLOWED)

    return {
        "source": "data/raw/tickets.csv",
        "fields": list(tickets.columns),
        "total_records": int(len(tickets)),
        "exact_duplicate_rows": int(tickets.duplicated(keep="first").sum()),
        "duplicate_ticket_id_rows": int(
            ticket_ids[ticket_ids.ne("")].duplicated(keep="first").sum()
        ),
        "missing_ticket_ids": int(ticket_ids.eq("").sum()),
        "missing_customer_ids": int(customer_ids.eq("").sum()),
        "unknown_customer_ids": int(
            (customer_ids.ne("") & ~customer_ids.isin(known_customer_ids)).sum()
        ),
        "empty_messages": int(messages.str.strip().eq("").sum()),
        "long_messages_over_400_tokens": int(
            messages.map(lambda message: mock_llm.est_tokens(message) > MAX_INPUT_TOKENS).sum()
        ),
        "missing_or_invalid_timestamps": int(timestamps.isna().sum()),
        "invalid_true_categories": int(invalid_categories.sum()),
        "true_category_counts": {
            str(category): int(count) for category, count in category_counts.items()
        },
        "cleaning_decisions": {
            "rows_dropped": 0,
            "empty_messages": "Retained and routed to Human Support Lead without an LLM call.",
            "long_messages": "Retained and routed to Human Support Lead without an LLM call.",
            "invalid_or_missing_fields": (
                "Retained and reported; records requiring manual attention are not "
                "silently assigned a model category."
            ),
            "true_category": (
                "Used only for aggregate data-quality reporting; never passed to the "
                "classifier or included in ticket_triage.csv."
            ),
        },
    }


def _premium_status(value: Any) -> str:
    normalized = str(value).strip().lower()
    if normalized in {"1", "1.0", "true"}:
        return "premium"
    if normalized in {"0", "0.0", "false"}:
        return "not_premium"
    return "unknown"


def build_enrichment_maps(
    segments: pd.DataFrame, retention: pd.DataFrame
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, Any]], int]:
    _require_columns(segments, SEGMENT_COLUMNS, "Part B customer_segments.csv")
    if segments["customer_id"].astype(str).str.strip().duplicated().any():
        raise ValueError("Part B customer_segments.csv contains duplicate customer IDs.")

    segment_map: dict[str, dict[str, str]] = {}
    for row in segments.to_dict(orient="records"):
        customer_id = str(row["customer_id"]).strip()
        if not customer_id:
            continue
        segment_name = str(row["segment_name"]).strip() or "unknown"
        segment_map[customer_id] = {
            "customer_segment": segment_name,
            "premium_status": _premium_status(row["is_premium"]),
        }

    lapse_map: dict[str, dict[str, Any]] = {}
    invalid_lapse_predictions = 0
    if not retention.empty:
        _require_columns(retention, RETENTION_COLUMNS, "Part B retention_list.csv")
        for row in retention.to_dict(orient="records"):
            customer_id = str(row["customer_id"]).strip()
            try:
                probability = float(row["lapse_probability"])
            except (TypeError, ValueError):
                invalid_lapse_predictions += 1
                continue
            if (
                not customer_id
                or not math.isfinite(probability)
                or not 0.0 <= probability <= 1.0
            ):
                invalid_lapse_predictions += 1
                continue
            if customer_id in lapse_map:
                raise ValueError(
                    "Part B retention_list.csv contains duplicate customer predictions."
                )
            lapse_map[customer_id] = {
                "lapse_probability": probability,
                "lapse_prediction": "lapsed" if probability >= 0.5 else "active",
            }
    return segment_map, lapse_map, invalid_lapse_predictions


def enrich_customer(
    customer_id: str,
    segment_map: dict[str, dict[str, str]],
    lapse_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    customer_id = str(customer_id).strip()
    if not customer_id:
        enrichment_status = "missing_customer_id"
        segment = {"customer_segment": "unknown", "premium_status": "unknown"}
    elif customer_id not in segment_map:
        enrichment_status = "unknown_customer_id"
        segment = {"customer_segment": "unknown", "premium_status": "unknown"}
    else:
        enrichment_status = "matched"
        segment = segment_map[customer_id]

    lapse = lapse_map.get(customer_id, {})
    return {
        **segment,
        "lapse_prediction": lapse.get("lapse_prediction"),
        "lapse_probability": lapse.get("lapse_probability"),
        "enrichment_status": enrichment_status,
    }


def route_ticket(
    category: str | None,
    processing_status: str,
    enrichment_status: str,
    customer_segment: str = "unknown",
    premium_status: str = "unknown",
    lapse_prediction: str | None = None,
) -> dict[str, str]:
    priority = "NORMAL"
    normalized_category = (category or "").strip().lower()
    if processing_status == "classified_json" and normalized_category in CATEGORY_TEAMS:
        assigned_team = CATEGORY_TEAMS[normalized_category]
        reason = f"Routed by validated ticket category: {normalized_category}."
        if enrichment_status != "matched":
            reason += " Customer enrichment is unavailable and did not change routing."
        else:
            reason += (
                f" Customer context (segment={customer_segment}, "
                f"premium={premium_status}, lapse="
                f"{lapse_prediction or 'unavailable'}) is informational only."
            )
    else:
        assigned_team = "Human Support Lead"
        reason = (
            f"Manual review required because classification status is "
            f"{processing_status}."
        )
    return {
        "priority": priority,
        "assigned_team": assigned_team,
        "routing_reason": reason,
    }


def _load_part_b_enrichment(
    outputs_dir: Path,
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, Any]], dict[str, Any]]:
    segments_path = outputs_dir / "customer_segments.csv"
    retention_path = outputs_dir / "retention_list.csv"
    diagnostics_path = outputs_dir / "lapse_model_diagnostics.json"
    if not segments_path.is_file():
        raise FileNotFoundError(f"Required Part B segment output not found: {segments_path}")

    segments = _read_csv(segments_path)
    if retention_path.is_file():
        retention = _read_csv(retention_path)
    else:
        retention = pd.DataFrame(columns=sorted(RETENTION_COLUMNS))
    segment_map, lapse_map, invalid_predictions = build_enrichment_maps(
        segments, retention
    )

    diagnostics: dict[str, Any] = {}
    if diagnostics_path.is_file():
        diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
        positive_class = diagnostics.get("positive_class", {})
        if positive_class and (
            positive_class.get("value") != 1
            or positive_class.get("meaning") != "lapsed"
        ):
            raise ValueError("Part B diagnostics do not identify lapsed as class 1.")

    return segment_map, lapse_map, {
        "segment_source_available": True,
        "retention_list_source_available": retention_path.is_file(),
        "diagnostics_source_available": diagnostics_path.is_file(),
        "segment_customers": len(segment_map),
        "valid_customer_lapse_predictions": len(lapse_map),
        "invalid_customer_lapse_predictions": invalid_predictions,
        "lapse_probability_source": "outputs/retention_list.csv",
        "lapse_prediction_threshold": 0.5,
    }


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _aggregate_counts(series: pd.Series) -> dict[str, int]:
    counts = series.fillna("unknown").replace("", "unknown").value_counts()
    return {str(key): int(value) for key, value in counts.items()}


def run_full_pipeline(
    prompt_type: str = "few_shot",
    token_budget: int = TOKEN_BUDGET,
    tickets_path: Path | None = None,
    outputs_dir: Path | None = None,
) -> pd.DataFrame:
    if token_budget < 0:
        raise ValueError("token_budget must be nonnegative.")
    outputs_dir = outputs_dir or OUTPUTS_DIR
    tickets_path = tickets_path or RAW_DIR / "tickets.csv"
    tickets = _read_csv(tickets_path)
    _require_columns(tickets, TICKET_COLUMNS, str(tickets_path))
    segment_map, lapse_map, enrichment_sources = _load_part_b_enrichment(outputs_dir)
    quality_report = audit_ticket_data(tickets, set(segment_map))

    mock_llm.reset()
    total_used = 0
    rows: list[dict[str, Any]] = []
    raw_messages = tickets["text"].fillna("").astype(str).tolist()
    for ticket in tickets.to_dict(orient="records"):
        original_message = str(ticket.get("text", "") or "")
        masked_message = redact_pii(original_message)
        ticket_id = str(ticket.get("ticket_id", "")).strip()
        customer_id = str(ticket.get("customer_id", "")).strip()
        enrichment = enrich_customer(customer_id, segment_map, lapse_map)
        processing_status = "classified_json"
        category: str | None = None
        reason = ""
        estimated_tokens = mock_llm.est_tokens(masked_message)

        if not ticket_id:
            processing_status = "flagged_missing_ticket_id"
        elif not masked_message.strip():
            processing_status = "skipped_empty"
        elif estimated_tokens > MAX_INPUT_TOKENS:
            processing_status = "flagged_long"
        elif total_used + estimated_tokens > token_budget:
            processing_status = "budget_exhausted"
        else:
            usage_before = mock_llm.get_usage()
            try:
                result = classify_ticket(masked_message, prompt_type=prompt_type)
                processing_status = result["status"]
                if processing_status == "classified_json":
                    payload = json.loads(result["text"])
                    category = str(payload["category"]).strip().lower()
                    reason = redact_pii(str(payload.get("reason", "")).strip())
            except Exception as error:
                processing_status = "model_error"
                reason = f"Model call failed: {type(error).__name__}."
            total_used += max(0, mock_llm.get_usage() - usage_before)

        routing = route_ticket(
            category,
            processing_status,
            enrichment["enrichment_status"],
            enrichment["customer_segment"],
            enrichment["premium_status"],
            enrichment["lapse_prediction"],
        )
        rows.append(
            {
                "ticket_id": ticket_id,
                "customer_id": customer_id,
                "masked_message": masked_message,
                "predicted_category": category,
                "classification_reason": reason,
                "priority": routing["priority"],
                "customer_segment": enrichment["customer_segment"],
                "premium_status": enrichment["premium_status"],
                "lapse_prediction": enrichment["lapse_prediction"],
                "lapse_probability": enrichment["lapse_probability"],
                "assigned_team": routing["assigned_team"],
                "routing_reason": routing["routing_reason"],
                "enrichment_status": enrichment["enrichment_status"],
                "processing_status": processing_status,
            }
        )

    output = pd.DataFrame(rows)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    output_path = outputs_dir / "ticket_triage.csv"
    output.to_csv(output_path, index=False)

    before_counts: Counter[str] = Counter()
    after_counts: Counter[str] = Counter()
    for original, masked in zip(raw_messages, output["masked_message"].tolist()):
        before_counts.update(count_redactions(original))
        after_counts.update(count_redactions(masked))
    privacy_report = {
        "total_messages": len(raw_messages),
        "messages_with_detected_pii": sum(
            any(count_redactions(message).values()) for message in raw_messages
        ),
        "detected_values_masked": dict(before_counts),
        "remaining_detected_values_in_masked_messages": dict(after_counts),
        "masking_patterns": {
            "emails": "Email-address pattern.",
            "phones": (
                "Indian 10-digit mobile numbers, optional +91/91/0 prefix, and "
                "international phone numbers with an explicit + country prefix."
            ),
            "order_ids": "ORD- followed by six digits.",
        },
        "name_detection": (
            "No customer-name field exists in the source customer data. "
            "Free-form names are not reliably detectable by these patterns."
        ),
        "limitations": (
            "Regex masking can miss unformatted, obfuscated, or nonstandard identifiers. "
            "Ordinary numbers are not masked unless they match a phone or order-ID pattern."
        ),
        "raw_messages_written_to_public_output": False,
    }

    status_counts = _aggregate_counts(output["processing_status"])
    category_counts = _aggregate_counts(output["predicted_category"])
    team_counts = _aggregate_counts(output["assigned_team"])
    priority_counts = _aggregate_counts(output["priority"])
    matched = int(output["enrichment_status"].eq("matched").sum())
    premium_covered = int(output["premium_status"].isin(["premium", "not_premium"]).sum())
    lapse_covered = int(output["lapse_prediction"].notna().sum())
    enrichment_report = {
        "total_tickets": len(output),
        "customers_successfully_matched": matched,
        "missing_customer_matches": len(output) - matched,
        "segment_enrichment_coverage": int(
            output["customer_segment"].ne("unknown").sum()
        ),
        "premium_enrichment_coverage": premium_covered,
        "lapse_prediction_coverage": lapse_covered,
        "lapse_predictions_missing_are_not_treated_as_active": True,
        "sources": enrichment_sources,
    }
    quality_report.update(
        {
            "records_written": len(output),
            "classification_status_counts": status_counts,
            "predicted_category_counts": category_counts,
            "customer_enrichment": enrichment_report,
        }
    )
    routing_report = {
        "priority_counts": priority_counts,
        "assigned_team_counts": team_counts,
        "processing_status_counts": status_counts,
        "predicted_category_counts": category_counts,
        "precedence": [
            "Validated ticket category selects its category support team.",
            "Fraud category routes to Fraud/Security Team.",
            "Missing or failed classification routes to Human Support Lead.",
            "Customer segment, premium status, and lapse prediction are context only.",
            (
                "Priority remains NORMAL because the ticket schema and current project "
                "design provide no severity scale or urgency rules."
            ),
        ],
        "lapse_prediction_threshold": 0.5,
    }

    _write_json(outputs_dir / "ticket_quality_report.json", quality_report)
    _write_json(outputs_dir / "privacy_masking_report.json", privacy_report)
    _write_json(outputs_dir / "ticket_routing_report.json", routing_report)
    print(
        f"Part C completed: {len(output)} tickets; "
        f"classification statuses={status_counts}; teams={team_counts}"
    )
    print(f"Saved ticket outputs to {outputs_dir}.")
    return output


def main() -> pd.DataFrame:
    return run_full_pipeline(prompt_type="few_shot", token_budget=TOKEN_BUDGET)


if __name__ == "__main__":
    main()
