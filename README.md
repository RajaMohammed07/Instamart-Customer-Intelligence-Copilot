# Instamart Customer Intelligence & Support Copilot

## Overview
This project implements an end-to-end customer intelligence and support workflow for an Instamart-style retail business. It combines data cleaning, SQL analysis, customer segmentation, churn prediction, privacy-aware ticket triage, and retrieval-augmented policy support. The solution uses synthetic data generated locally, a SQLite database, and the offline `mock_llm.py` module to simulate LLM behavior, avoiding external APIs.

The project is organised into four connected parts:
1. Part A: Data foundation and trusted analytics layer.
2. Part B: RFM segmentation and lapse prediction.
3. Part C: Support ticket triage with privacy and guardrails.
4. Part D: Policy retrieval and refund agent.

The stack includes Python 3.11+, pandas, numpy, scikit-learn, sqlite3, and joblib.

## Reproduce
Run the following commands from a clean clone on Windows:

1. `python -m venv venv`
2. `venv\Scripts\activate`
3. `python -m pip install -r requirements.txt`
4. `python generate_data.py`
5. `python run_project.py`
6. `python -m src.part_a.clean_data`
7. `python -m src.part_b.customer_segmentation`
8. `python -m src.part_b.lapse_prediction`
9. `python -m src.part_c.ticket_routing`
10. `python -m src.part_d.refund_agent`
11. `python -m src.part_d.policy_assistant`

Validation checks are included in the scripts and the project prints `ALL CHECKPOINTS PASSED` for the data-cleaning stage when the pipeline succeeds.

## Part A
Part A converts raw exports into clean analytics data and stores the result in SQLite.

- Raw audit: the generator produces customer, product, and order files that are read and cleaned.
- Customer cleaning: city standardisation, gender harmonisation, age imputation with city medians, and date conversion.
- Order cleaning: duplicate removal, status harmonisation, numeric conversion, price merges, and delivery-time repair.
- Database creation: `data/instamart.db` contains `customers`, `products`, and `orders` tables.
- SQL execution: the SQL files in `sql/queries.sql` are read with `pd.read_sql_query()`.
- Validation: the project asserts the essential checkpoint conditions and prints `ALL CHECKPOINTS PASSED`.

## Part B
Part B builds an RFM profile for every customer, then clusters customers into actionable segments.

- RFM metrics are calculated from completed orders only.
- K-means is run for K=2 to 8 and the final segmentation uses a business-friendly K=4 choice.
- PCA reduces the RFM features to two components and reports explained variance.
- Lapse prediction builds a cohort from orders before the cut-off date and predicts likely churn using a logistic-regression pipeline and random-forest comparison.
- Model results are saved to `outputs/lapse_model.joblib`.
- Retention candidates are exported to `outputs/retention_list.csv`.

## Part C
Part C protects privacy and classifies support tickets.

- PII is redacted from ticket text before any model call.
- The system checks for empty tickets and long tickets before sending content to the mock LLM.
- Zero-shot and few-shot prompts are used in the classification flow.
- Retry logic and output validation ensure that invalid responses are detected and handled safely.
- Final routing outputs are written to `outputs/triage_results.csv` and `outputs/triage_budget_demo.csv`.

## Part D
Part D implements a retrieval-grounded policy assistant and a tool-using refund agent.

- The policy documents in `data/policies` are chunked into overlapping text blocks and ranked with TF-IDF.
- The assistant answers policy questions using retrieved context only.
- The refund agent checks order eligibility, searches policy text, calculates refunds, and updates the ledger.
- All scenario runs are stored as JSON Lines in `outputs/agent_runs.jsonl`.
- The refund ledger is maintained in `outputs/refund_ledger.jsonl`.

## Limitations and Next Steps
- The dataset is synthetic and intended for educational and project-based learning.
- The offline `mock_llm.py` is a simulation, not a production-grade LLM service.
- TF-IDF is effective for lexical retrieval but cannot fully understand semantics.
- The lapse model is based on historical summary features and should be monitored in production.
- A real deployment would require stronger observability, safer data controls, and a production database and queueing system.

This project is designed to be reproducible and explainable in an interview setting, while demonstrating the full lifecycle of a real customer intelligence and support assistant.
