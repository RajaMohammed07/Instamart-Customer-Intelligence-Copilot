from __future__ import annotations

import json
import random
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence


class TransientLLMError(RuntimeError):
    """Simulates retryable transient failures for the offline LLM."""


@dataclass
class Usage:
    total_tokens: int = 0


class MockLLM:
    def __init__(self):
        self.reset()

    def reset(self):
        self.calls = 0
        self.failures = 0
        self.usage = Usage()

    @staticmethod
    def est_tokens(text: str) -> int:
        return max(1, len(re.findall(r"\S+", text)))

    def chat(self, messages: Sequence[Dict[str, str]], model: str | None = None):
        self.calls += 1
        combined = '\n'.join(m.get('content', '') for m in messages)
        lower = combined.lower()
        if 'fraud' in lower or 'security team' in lower:
            result = '{"category": "fraud", "reason": "Potential fraudulent activity detected."}'
        elif 'billing' in lower or 'refund' in lower:
            result = '{"category": "billing", "reason": "Customer is asking about a payment or billing issue."}'
        elif 'delivery' in lower or 'late' in lower:
            result = '{"category": "delivery", "reason": "Problem relates to a delivery or shipping delay."}'
        elif 'crash' in lower or 'technical' in lower or 'error' in lower:
            result = '{"category": "technical", "reason": "Issue indicates technical product or application failure."}'
        else:
            result = '{"category": "billing", "reason": "Default safe classification."}'

        if self.calls % 13 == 0:
            self.failures += 1
            raise TransientLLMError('transient error')
        self.usage.total_tokens += self.est_tokens(combined)
        return {"content": result, "usage": self.usage}


llm = MockLLM()


def reset():
    llm.reset()


def est_tokens(text: str) -> int:
    return llm.est_tokens(text)


def chat(messages: Sequence[Dict[str, str]], model: str | None = None):
    return llm.chat(messages, model=model)


def get_usage():
    return llm.usage.total_tokens


def set_seed(seed: int):
    random.seed(seed)
