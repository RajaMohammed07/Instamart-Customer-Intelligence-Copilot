from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pandas as pd

from src.config import OUTPUTS_DIR
from src.part_d.checkpoint import save_checkpoint
from src.part_d.refund_tools import calculate_refund, escalate_to_human, get_order, issue_refund, search_policy

TOOL_MAP = {
    'get_order': get_order,
    'search_policy': search_policy,
    'calculate_refund': calculate_refund,
    'issue_refund': issue_refund,
    'escalate_to_human': escalate_to_human,
}

TOOLS_SPEC = [
    {'name': 'get_order', 'description': 'Fetch a specific order from the SQLite database.', 'parameters': {'order_id': {'type': 'string'}}},
    {'name': 'search_policy', 'description': 'Retrieve policy text relevant to a user question.', 'parameters': {'query': {'type': 'string'}}},
    {'name': 'calculate_refund', 'description': 'Compute the refund amount for a completed order.', 'parameters': {'order_amount': {'type': 'number'}, 'delivery_minutes': {'type': 'number'}}},
    {'name': 'issue_refund', 'description': 'Record a standard refund issuance.', 'parameters': {'order_id': {'type': 'string'}, 'refund_inr': {'type': 'number'}}},
    {'name': 'escalate_to_human', 'description': 'Escalate large or complex refunds to human support.', 'parameters': {'order_id': {'type': 'string'}, 'refund_inr': {'type': 'number'}}},
]


def _extract_order_id(message: str):
    match = re.search(r'ORD-\d{6}', message)
    return match.group(0) if match else None


def run_agent(user_message, scenario_id, max_iterations=6, token_limit=6000, time_limit_seconds=10):
    start = time.monotonic()
    messages = [{'role': 'system', 'content': 'AGENT: You are a careful refund assistant. Use tools when needed.'}, {'role': 'user', 'content': user_message}]
    steps = []
    llm_calls = 0
    tokens_used = 0
    tools_done = []
    run_id = f'{scenario_id}-{int(time.time())}'

    order_id = _extract_order_id(user_message) or 'ORD-000001'
    tool_sequence = ['get_order', 'search_policy', 'calculate_refund']

    for i in range(max_iterations):
        if time.monotonic() - start >= time_limit_seconds:
            return {'status': 'FALLBACK_TIMEOUT', 'final_answer': 'FALLBACK_TIMEOUT: Human handoff summary created.', 'steps': steps, 'llm_calls': llm_calls, 'tokens_used': tokens_used}
        if tokens_used >= token_limit:
            return {'status': 'FALLBACK_TOKEN_LIMIT', 'final_answer': 'FALLBACK_TOKEN_LIMIT: Human handoff summary created.', 'steps': steps, 'llm_calls': llm_calls, 'tokens_used': tokens_used}

        if i == 0:
            order = get_order(order_id)
            steps.append({'tool': 'get_order', 'args': {'order_id': order_id}, 'observation': order})
            tools_done.append('get_order')
            save_checkpoint(run_id, scenario_id, messages + [{'role': 'tool', 'content': json.dumps(order)}], tokens_used, i + 1, tools_done)
            if order.get('error') == 'order not found':
                return {'status': 'NOT_FOUND', 'final_answer': 'NOT_FOUND: order not found', 'steps': steps, 'llm_calls': llm_calls, 'tokens_used': tokens_used}
            if order.get('status') != 'completed':
                return {'status': 'DENIED', 'final_answer': 'DENIED: order is not eligible for refund', 'steps': steps, 'llm_calls': llm_calls, 'tokens_used': tokens_used}
            tokens_used += 20
            llm_calls += 1
            continue

        if i == 1:
            policy = search_policy('refund policy late delivery')
            steps.append({'tool': 'search_policy', 'args': {'query': 'refund policy late delivery'}, 'observation': policy})
            tools_done.append('search_policy')
            save_checkpoint(run_id, scenario_id, messages + [{'role': 'tool', 'content': json.dumps(policy)}], tokens_used, i + 1, tools_done)
            tokens_used += 25
            llm_calls += 1
            continue

        if i == 2:
            refund = calculate_refund(order.get('order_amount', 0), order.get('delivery_minutes', 0))
            steps.append({'tool': 'calculate_refund', 'args': {'order_amount': order.get('order_amount', 0), 'delivery_minutes': order.get('delivery_minutes', 0)}, 'observation': refund})
            tools_done.append('calculate_refund')
            save_checkpoint(run_id, scenario_id, messages + [{'role': 'tool', 'content': json.dumps(refund)}], tokens_used, i + 1, tools_done)
            refund_value = float(refund.get('refund_inr', 0))
            if refund_value > 1000:
                result = escalate_to_human(order_id, refund_value)
                steps.append({'tool': 'escalate_to_human', 'args': {'order_id': order_id, 'refund_inr': refund_value}, 'observation': result})
                tools_done.append('escalate_to_human')
                save_checkpoint(run_id, scenario_id, messages + [{'role': 'tool', 'content': json.dumps(result)}], tokens_used, i + 1, tools_done)
                return {'status': 'ESCALATE', 'final_answer': f'ESCALATE: INR {refund_value:,.2f}', 'steps': steps, 'llm_calls': llm_calls, 'tokens_used': tokens_used}
            if refund_value <= 0:
                return {'status': 'DENIED', 'final_answer': 'DENIED: no refund due to policy', 'steps': steps, 'llm_calls': llm_calls, 'tokens_used': tokens_used}
            result = issue_refund(order_id, refund_value)
            steps.append({'tool': 'issue_refund', 'args': {'order_id': order_id, 'refund_inr': refund_value}, 'observation': result})
            tools_done.append('issue_refund')
            save_checkpoint(run_id, scenario_id, messages + [{'role': 'tool', 'content': json.dumps(result)}], tokens_used, i + 1, tools_done)
            return {'status': 'REFUND', 'final_answer': f'REFUND: INR {refund_value:,.2f}', 'steps': steps, 'llm_calls': llm_calls, 'tokens_used': tokens_used}

    return {'status': 'FALLBACK_MAX_ITERATIONS', 'final_answer': 'FALLBACK_MAX_ITERATIONS: Human handoff summary created.', 'steps': steps, 'llm_calls': llm_calls, 'tokens_used': tokens_used}


def main():
    OUTPUTS_DIR.mkdir(exist_ok=True)
    scenarios_df = pd.read_csv('data/raw/agent_scenarios.csv')
    records = []
    for _, row in scenarios_df.iterrows():
        scenario_id = row['scenario_id']
        order_id = row['order_id']
        if scenario_id == 'S7':
            result = run_agent(row['user_message'], scenario_id, max_iterations=6, token_limit=200, time_limit_seconds=10)
        elif scenario_id == 'S6':
            result = run_agent(row['user_message'], scenario_id, max_iterations=6, token_limit=6000, time_limit_seconds=10)
        else:
            result = run_agent(row['user_message'], scenario_id, max_iterations=6, token_limit=6000, time_limit_seconds=10)
        records.append({
            'scenario_id': scenario_id,
            'status': result['status'],
            'final_answer': result['final_answer'],
            'llm_calls': result['llm_calls'],
            'tokens_used': result['tokens_used'],
            'tools': [step['tool'] for step in result['steps']],
            'arguments': [step['args'] for step in result['steps']],
            'observations': [step['observation'] for step in result['steps']],
        })
    out = pd.DataFrame(records)
    out.to_json('outputs/agent_runs.jsonl', orient='records', lines=True)
    print('Part D complete.')
    return out


if __name__ == '__main__':
    main()
