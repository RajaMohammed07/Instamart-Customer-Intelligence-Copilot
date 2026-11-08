from __future__ import annotations

import json
import re
import time
from typing import Any

import mock_llm

from src.part_c.privacy import redact_pii

MAX_RETRIES = 3
BASE_DELAY = 0.05
MAX_INPUT_TOKENS = 400
ALLOWED = {"billing", "delivery", "technical", "fraud"}
FRAUD_INDICATOR_PATTERN = re.compile(
    r"\b(?:fraud|security team|unauthori[sz]ed|not my purchase|not me|"
    r"someone used my account|somebody used my account|account was hacked|"
    r"stolen account|unusual (?:duplicate )?charge)\b",
    re.IGNORECASE,
)


def parse_classification(text: str) -> str:
    try:
        payload = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return "flagged_invalid_output"
    if not isinstance(payload, dict):
        return "flagged_invalid_output"
    category = payload.get("category")
    if isinstance(category, str) and category.strip().lower() in ALLOWED:
        return "classified_json"
    return "flagged_invalid_output"


def _response_text(response: Any) -> str:
    if not isinstance(response, dict):
        return ""
    content = response.get("content")
    if isinstance(content, dict):
        content = content.get("content")
    return content if isinstance(content, str) else ""


def classify_ticket(ticket_text: str, prompt_type: str = "few_shot") -> dict[str, Any]:
    if prompt_type not in {"zero_shot", "few_shot"}:
        raise ValueError(f"Unsupported prompt type: {prompt_type}")

    masked_text = redact_pii(ticket_text)
    if not masked_text.strip():
        return {"text": "", "attempts": 0, "status": "skipped_empty"}
    if mock_llm.est_tokens(masked_text) > MAX_INPUT_TOKENS:
        return {"text": "", "attempts": 0, "status": "flagged_long"}

    for attempt in range(MAX_RETRIES):
        try:
            response = mock_llm.chat(
                [{"role": "user", "content": masked_text}]
            )
            text = _response_text(response)
            if (
                parse_classification(text) == "classified_json"
                and FRAUD_INDICATOR_PATTERN.search(masked_text)
            ):
                payload = json.loads(text)
                payload["category"] = "fraud"
                payload["reason"] = (
                    "Potential unauthorized account or suspicious charge activity."
                )
                text = json.dumps(payload)
            return {
                "text": text,
                "attempts": attempt + 1,
                "status": parse_classification(text),
            }
        except mock_llm.TransientLLMError:
            if attempt + 1 == MAX_RETRIES:
                raise RuntimeError("Model call failed after retries") from None
            time.sleep(BASE_DELAY * (2**attempt))

    raise RuntimeError("Model call failed after retries")
