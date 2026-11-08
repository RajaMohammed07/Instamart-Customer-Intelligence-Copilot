from __future__ import annotations

import re


EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.IGNORECASE)
INDIAN_PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?91[\s().-]?)?(?:0)?[6-9](?:[\s().-]?\d){9}(?!\d)"
)
INTERNATIONAL_PHONE_PATTERN = re.compile(
    r"(?<!\w)\+(?!91\b)\d{1,3}(?:[\s().-]*\d){7,12}(?!\w)"
)
ORDER_ID_PATTERN = re.compile(r"\bORD-\d{6}\b", re.IGNORECASE)


def redact_pii(text: str | None) -> str:
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    text = EMAIL_PATTERN.sub("[EMAIL]", text)
    text = ORDER_ID_PATTERN.sub("[ORDER_ID]", text)
    text = INTERNATIONAL_PHONE_PATTERN.sub("[PHONE]", text)
    return INDIAN_PHONE_PATTERN.sub("[PHONE]", text)


def count_redactions(text: str | None) -> dict[str, int]:
    if text is None:
        return {"emails": 0, "phones": 0, "order_ids": 0}
    if not isinstance(text, str):
        text = str(text)

    international_phones = INTERNATIONAL_PHONE_PATTERN.findall(text)
    without_international = INTERNATIONAL_PHONE_PATTERN.sub("", text)
    indian_phones = INDIAN_PHONE_PATTERN.findall(without_international)
    return {
        "emails": len(EMAIL_PATTERN.findall(text)),
        "phones": len(international_phones) + len(indian_phones),
        "order_ids": len(ORDER_ID_PATTERN.findall(text)),
    }
