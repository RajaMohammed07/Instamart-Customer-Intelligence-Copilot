from __future__ import annotations

import json
import random
import re
import time
from typing import Any, Dict, List

import mock_llm
from src.part_c.privacy import redact_pii

MAX_RETRIES = 3
BASE_DELAY = 0.05
ALLOWED = {'billing', 'delivery', 'technical', 'fraud'}


def classify_ticket(ticket_text: str, prompt_type: str = 'few_shot') -> Dict[str, Any]:
    prompt = {'zero_shot': 'CLASSIFY the ticket below into one of: billing, delivery, technical, fraud. Return JSON only in the format: {"category": "...", "reason": "..."}\n',
              'few_shot': 'CLASSIFY the ticket below into one of: billing, delivery, technical, fraud. Return JSON only in the format: {"category": "...", "reason": "..."}\nEXAMPLES:\n1. "My account shows a duplicate charge" -> {"category": "billing", "reason": "duplicate charge"}\n2. "The app crashes" -> {"category": "technical", "reason": "app crash"}\n3. "Unknown charge from my account" -> {"category": "fraud", "reason": "possible fraud"}\n'}[prompt_type]
    for attempt in range(MAX_RETRIES):
        try:
            response = mock_llm.chat([{'role': 'user', 'content': prompt + ticket_text}])
            return {'text': response['content']['content'] if isinstance(response['content'], dict) else response['content'], 'attempts': attempt + 1}
        except mock_llm.TransientLLMError:
            wait = BASE_DELAY * (2 ** attempt) * random.uniform(0.9, 1.15)
            time.sleep(wait)
    raise RuntimeError('Model call failed after retries')


def parse_classification(text: str) -> str:
    try:
        payload = json.loads(text)
        category = payload.get('category', '').strip().lower()
        if category in ALLOWED:
            return 'classified_json'
    except Exception:
        pass
    words = re.findall(r'[a-z]+', text.lower())
    matches = [w for w in words if w in ALLOWED]
    if len(matches) == 1:
        return 'classified_keyword'
    return 'flagged_invalid_output'
