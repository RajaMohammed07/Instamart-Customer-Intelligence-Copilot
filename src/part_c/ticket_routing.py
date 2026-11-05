from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pandas as pd

import mock_llm
from src.config import CLEAN_DIR, OUTPUTS_DIR
from src.part_c.classifier import MAX_RETRIES, classify_ticket, parse_classification
from src.part_c.privacy import redact_pii

MAX_INPUT_TOKENS = 400
TOKEN_BUDGET = 100000


def run_full_pipeline(prompt_type: str = 'few_shot', token_budget: int = TOKEN_BUDGET):
    tickets = pd.read_csv('data/raw/tickets.csv')
    segments = pd.read_csv('outputs/customer_segments.csv') if Path('outputs/customer_segments.csv').exists() else pd.DataFrame()
    rows = []
    total_used = 0
    mock_llm.reset()
    for _, row in tickets.iterrows():
        ticket_text = str(row['text'])
        ticket_id = row['ticket_id']
        if ticket_text.strip() == '':
            status = 'skipped_empty'
            category = ''
            route = 'human_review'
            priority = 'NORMAL'
            tokens_used = 0
            rows.append({
                'ticket_id': ticket_id,
                'customer_id': row['customer_id'],
                'status': status,
                'category': category,
                'segment_name': '',
                'priority': priority,
                'route': route,
                'tokens_used': tokens_used
            })
            continue

        tokens = mock_llm.est_tokens(ticket_text)
        if tokens > MAX_INPUT_TOKENS:
            status = 'flagged_long'
            rows.append({
                'ticket_id': ticket_id,
                'customer_id': row['customer_id'],
                'status': status,
                'category': '',
                'segment_name': '',
                'priority': 'NORMAL',
                'route': 'human_review',
                'tokens_used': tokens,
            })
            continue

        redacted = redact_pii(ticket_text)
        assert not re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', redacted)
        assert not re.search(r'\b[6-9]\d{9}\b', redacted)
        assert not re.search(r'ORD-\d{6}', redacted)

        if total_used >= token_budget:
            rows.append({
                'ticket_id': ticket_id,
                'customer_id': row['customer_id'],
                'status': 'budget_exhausted',
                'category': '',
                'segment_name': '',
                'priority': 'NORMAL',
                'route': 'human_review',
                'tokens_used': 0,
            })
            continue

        result = classify_ticket(redacted, prompt_type=prompt_type)
        text = result['text']
        classification = parse_classification(text)
        category = ''
        if classification == 'classified_json':
            try:
                payload = json.loads(text)
                category = str(payload.get('category', '')).strip().lower()
                if category not in {'billing', 'delivery', 'technical', 'fraud'}:
                    category = ''
            except Exception:
                category = ''
        elif classification == 'classified_keyword':
            words = re.findall(r'[a-z]+', text.lower())
            allowed = [w for w in words if w in {'billing', 'delivery', 'technical', 'fraud'}]
            category = allowed[0] if len(allowed) == 1 else ''
        else:
            category = ''
        if category == '':
            status = 'flagged_invalid_output'
        else:
            status = 'classified_json' if classification == 'classified_json' else 'classified_keyword'
        total_used += max(1, mock_llm.get_usage())
        rows.append({
            'ticket_id': ticket_id,
            'customer_id': row['customer_id'],
            'status': status,
            'category': category,
            'segment_name': '',
            'priority': 'NORMAL',
            'route': 'support_queue',
            'tokens_used': max(1, mock_llm.get_usage()),
        })
    out = pd.DataFrame(rows)
    out.to_csv(OUTPUTS_DIR / 'triage_results.csv', index=False)
    return out


def main():
    OUTPUTS_DIR.mkdir(exist_ok=True)
    results = run_full_pipeline(prompt_type='few_shot', token_budget=100000)
    print('Part C complete with', len(results), 'rows.')
    return results


if __name__ == '__main__':
    main()
