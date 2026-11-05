from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.part_a.clean_data import main as part_a_main
from src.part_b.customer_segmentation import main as part_b_main
from src.part_c.ticket_routing import main as part_c_main
from src.part_d.refund_agent import main as part_d_main


def run_all():
    print('Running Part A: Data Foundation')
    part_a_main()
    print('Running Part B: Customer Segmentation and Lapse Prediction')
    part_b_main()
    print('Running Part C: Support Ticket Triage')
    part_c_main()
    print('Running Part D: Policy RAG and Refund Agent')
    part_d_main()
    print('Project run complete.')


if __name__ == '__main__':
    run_all()
