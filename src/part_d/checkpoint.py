from __future__ import annotations

import json
from pathlib import Path

STATE_DIR = Path('state')
STATE_DIR.mkdir(exist_ok=True)


def save_checkpoint(run_id: str, scenario_id: str, messages: list, tokens_used: int, step: int, tools_done: list):
    payload = {
        'run_id': run_id,
        'scenario_id': scenario_id,
        'messages': messages,
        'tokens_used': tokens_used,
        'step': step,
        'tools_done': tools_done,
    }
    path = STATE_DIR / f'{run_id}.json'
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return path


def resume_agent(run_id: str):
    path = STATE_DIR / f'{run_id}.json'
    if not path.exists():
        raise FileNotFoundError(f'Checkpoint {run_id} not found')
    payload = json.loads(path.read_text(encoding='utf-8'))
    return payload
