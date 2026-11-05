from __future__ import annotations

import re

EMAIL_PATTERN = r'[\w.+-]+@[\w-]+\.[\w.]+'
PHONE_PATTERN = r'\b[6-9]\d{9}\b'
ORDER_ID_PATTERN = r'ORD-\d{6}'


def redact_pii(text: str) -> str:
    text = re.sub(EMAIL_PATTERN, '[EMAIL]', text)
    text = re.sub(PHONE_PATTERN, '[PHONE]', text)
    text = re.sub(ORDER_ID_PATTERN, '[ORDER_ID]', text)
    return text


def count_redactions(text: str):
    emails = re.findall(EMAIL_PATTERN, text)
    phones = re.findall(PHONE_PATTERN, text)
    order_ids = re.findall(ORDER_ID_PATTERN, text)
    return {'emails': len(emails), 'phones': len(phones), 'order_ids': len(order_ids)}
