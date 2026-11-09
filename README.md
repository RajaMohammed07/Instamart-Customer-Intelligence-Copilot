# Overview

## Project Overview & Business Problem

The Instamart Customer Intelligence & Support Copilot implements an end-to-end customer analytics and support intelligence pipeline for quick-commerce and retail operations.

In high-velocity retail environments, business teams must balance four critical challenges:

- **Data Trust & Transaction Reconciliation:** Auditing messy raw transactional data, reconciling multi-city catalogue orders, enforcing chronological validity, and establishing a single source of truth in SQLite.
- **Customer Retention & Lapse Intervention:** Computing RFM (Recency, Frequency, Monetary) metrics, discovering behavioral clusters, and predicting customer lapse before churn occurs.
- **Privacy-Safe Customer Support Triage:** Ingesting incoming customer support inquiries, redacting personally identifiable information (PII) before LLM exposure, and safely routing tickets to specialized support desks.
- **Policy-Grounded Refund Guidance:** Assessing refund eligibility against published store policies using read-only SQL queries and retrieval-augmented citations without fabricating facts or authorizing unverified payouts.

The system is designed for complete local reproducibility, using synthetic transactional datasets and a local deterministic mock LLM simulation (`mock_llm.py`), eliminating external network API dependencies and costs.

## Features & Architecture

The project consists of four modules:

- **Part A – Data Foundation:** Raw data auditing, cleaning, SQLite database creation, validation, and analytical SQL queries.
- **Part B – Customer Intelligence:** RFM analysis, K-Means customer segmentation, PCA, lapse prediction, model evaluation, and retention prioritization.
- **Part C – Support Ticket Triage:** Ticket quality checks, PII masking, classification, customer-segment enrichment, and support queue routing.
- **Part D – Policy RAG & Refund Agent:** Policy retrieval, source-grounded answers, read-only order verification, and refund eligibility assessment.

**Component Separation:** Part C (ticket triage) and Part D (refund agent) operate independently. Part D evaluates standalone scenario inquiries and does not consume Part C triaged ticket context; ticket-context integration is not implemented.

## Technology Stack

| Area | Technologies |
|---|---|
| Language & Runtime | Python 3.11+ (tested on Python 3.14.2) |
| Data Engineering | pandas, NumPy |
| Machine Learning | scikit-learn: KMeans, PCA, LogisticRegression, RandomForestClassifier, StandardScaler, OneHotEncoder |
| Model Persistence | joblib |
| Database | SQLite 3, Python standard-library sqlite3 |
| NLP & Retrieval | TF-IDF, TfidfVectorizer, cosine similarity |
| LLM Simulation | Offline deterministic keyword-matching module (`mock_llm.py`) |
| Testing | Python standard-library unittest |

## Repository Structure

```text
Instamart-Customer-Intelligence-Copilot/
│
├── .gitignore
├── README.md
├── requirements.txt
├── run_project.py
├── generate_data.py
├── mock_llm.py
│
├── archive/
│   └── part_b_final/
│       ├── README.md
│       ├── SHA256SUMS.txt
│       ├── outputs/
│       └── src/part_b/
│
├── data/
│   ├── clean/
│   │   ├── customers.csv
│   │   ├── orders.csv
│   │   └── products.csv
│   │
│   ├── policies/
│   │   ├── assignment_rules.txt
│   │   ├── delivery_policy.txt
│   │   ├── escalation_policy.txt
│   │   ├── payment_policy.txt
│   │   ├── privacy_policy.txt
│   │   └── refund_policy.txt
│   │
│   ├── raw/
│   │   ├── agent_scenarios.csv
│   │   ├── customers.csv
│   │   ├── orders.csv
│   │   ├── policy_eval.csv
│   │   ├── products.csv
│   │   └── tickets.csv
│   │
│   └── instamart.db
│
├── outputs/
│   ├── customer_segment_profiles.csv
│   ├── customer_segments.csv
│   ├── data_preservation_report.json
│   ├── lapse_forest_model.joblib
│   ├── lapse_model.joblib
│   ├── lapse_model_diagnostics.json
│   ├── lapse_oversampled_logistic_model.joblib
│   ├── lapse_test_predictions.csv
│   ├── part_b_final_report.md
│   ├── privacy_masking_report.json
│   ├── refund_assessments.jsonl
│   ├── retention_list.csv
│   ├── rfm_analysis.csv
│   ├── rfm_kmeans_metrics.csv
│   ├── rfm_pca_explained_variance.csv
│   ├── ticket_quality_report.json
│   ├── ticket_routing_report.json
│   ├── ticket_triage.csv
│   ├── triage_results.csv
│   ├── triage_budget_demo.csv
│   ├── agent_runs.jsonl
│   └── refund_ledger.jsonl
│
├── reports/
│   ├── final_project_completion_report.md
│   ├── final_repository_hygiene_audit.md
│   └── ticket_contact_provenance_and_sanitization.md
│
├── sql/
│   └── queries.sql
│
├── src/
│   ├── config.py
│   ├── part_a/
│   │   ├── clean_data.py
│   │   ├── data_audit.py
│   │   ├── database.py
│   │   ├── sql_analysis.py
│   │   └── validation.py
│   │
│   ├── part_b/
│   │   ├── customer_segmentation.py
│   │   ├── lapse_prediction.py
│   │   ├── retention.py
│   │   └── rfm_analysis.py
│   │
│   ├── part_c/
│   │   ├── classifier.py
│   │   ├── privacy.py
│   │   ├── prompts.py
│   │   └── ticket_routing.py
│   │
│   └── part_d/
│       ├── checkpoint.py
│       ├── policy_assistant.py
│       ├── policy_retrieval.py
│       ├── refund_agent.py
│       └── refund_tools.py
│
└── tests/
    ├── test_integration.py
    ├── test_part_b.py
    ├── test_part_c.py
    └── test_part_d.py
```

---

# Reproduce

## Requirements

- Operating System: Windows, macOS, or Linux.
- Python: Version 3.11 or newer (tested on Python 3.14.2).
- SQLite: Standard-library `sqlite3`; no external SQLite server installation is required.

## Environment Setup

Run the following commands from the repository root directory.

**1. Create a virtual environment**

```bash
python -m venv venv
```

**2. Activate the virtual environment**

Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
source venv/bin/activate
```

**3. Install dependencies**

```bash
python -m pip install -r requirements.txt
```

## Execution Instructions

Choose one execution route depending on your workflow. Do not run the full pipeline and then repeat all component commands.

### Route 1: Full Pipeline

`run_project.py` executes Parts A, B, C, and D in sequence.

It cleans raw data, recreates `data/instamart.db`, trains Part B models, writes outputs, runs Part C ticket triage, and generates Part D refund assessments.

It does not run `generate_data.py` or the standalone policy assistant.

```bash
python generate_data.py
python run_project.py
```

### Route 2: Individual Component Execution

Use these commands when inspecting or executing a specific part.

**Part A – Data Foundation & Database Rebuild**

Cleans raw CSVs, creates `data/instamart.db`, and executes all 19 validation checkpoints.

```bash
python -m src.part_a.clean_data
```

**Part A – SQL Analytics & EDA**

Runs the seven analytical queries in `sql/queries.sql` and cross-checks revenue with a Pandas pivot.

```bash
python -m src.part_a.sql_analysis
```

**Part B – Segmentation & Lapse ML**

Computes RFM metrics, fits K-Means (K=3), runs 2D PCA, trains lapse models, and writes retention outreach lists.

```bash
python -m src.part_b.customer_segmentation
```

**Part C – Support Ticket Triage**

Redacts PII, triages tickets with `mock_llm.py` and safety overrides, enriches records with customer segments, and generates audit reports.

```bash
python -m src.part_c.ticket_routing
```

**Part D – Refund Assessment Agent**

Evaluates sample refund scenarios against policy rules and read-only order lookups.

```bash
python -m src.part_d.refund_agent
```

### Route 3: Standalone Demonstrations & Safe Verification

**Standalone Policy Assistant**

Demonstrates grounded lexical retrieval answering policy questions with exact citations.

```bash
python -m src.part_d.policy_assistant
```

**Automated Testing**

Executes the automated unit and integration tests across Parts B, C, D, and end-to-end integration:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

The verified test suite reports 45 passing tests (5 Part B tests, 17 Part C tests, 18 Part D tests, and 5 integration tests) with 0 failures and 0 errors.

---

# Part A

## Data Foundation & Analytics Layer

Part A audits the canonical tracked CSVs, cleans them, builds SQLite tables, runs seven SQL queries, and cross-checks completed revenue with a Pandas pivot.

## Observed Raw Data Audit

| File | Rows | Columns | Observations |
|---|---:|---:|---|
| customers.csv | 1,200 | 5 | 20 blank ages, 3 ages outside 10–100, 30 blank genders, 7 city spelling variants |
| products.csv | 40 | 4 | Complete catalogue; prices range from INR 1,453.67 to INR 2,935.15 |
| orders.csv | 13,084 | 9 | 656 exact duplicate rows, 119 repeated order IDs after deduplication, 662 pending orders |
| tickets.csv | 164 | 5 | 4 ground-truth categories (41 each), 14 empty messages, contact-shaped patterns in 22 rows |

Additional order data-quality observations:

- 12,308 blank amounts.
- 776 invalid nonblank amounts.
- 106 negative delivery values.
- 12,978 blank delivery values.

## Cleaning & Validation

**Preservation of Business Records**

`generate_data.py` adjusts only:

- `orders.order_ts`, mapped to 2025-04-01 through 2025-09-30.
- `customers.signup_date`, mapped to 2024-04-04 through 2025-08-02, preceding first non-pending orders.

All customer attributes, product prices, order amounts, and quantities are preserved.

**Cleaned Dimensions**

Customers:

- 1,200 rows.
- Cities: Pune 218, Delhi 204, Bengaluru 201, Mumbai 201, Chennai 197, Hyderabad 179.
- Genders: female 594, male 547, unknown 59.
- Ages: imputed within the range 18–60.

Orders:

- 12,309 unique IDs.
- Completed: 11,430.
- Pending: 662.
- Cancelled: 217.

**Completed Revenue:** INR 41,822,667.48.

**Missing Delivery Times**

Raw data contains zero usable completed-order delivery times (12,978 blank, 106 negative). All 11,430 completed delivery values are correctly left missing rather than fabricated.

**SQLite Database**

The rebuilt `data/instamart.db` passes all 19 Part A validation checkpoints.

## SQL & Pandas Reconciliation

| Query | Actual Result | Assignment Reference | Status & Evidence |
|---|---|---|---|
| Q1 – Completed spend filter | 1,184 customers | 30 | Preserved source records yield 1,184 qualifying customers |
| Q2 – Revenue by city/category | 24 combinations; INR 41,822,667.48 | 30 combinations | Current data contains 6 cities and 4 categories (6 × 4 = 24) |
| Q3 – Above-average products | 18 products | 11 | Preserved product catalogue has 18 items above mean catalogue price |
| Q4 – Customers without orders | 0 customers | 25 | Every customer in the cleaned dataset has at least one completed order |
| Q5 – Above-average spenders | 566 customers (mean spend INR 34,852.22) | 550 | Follows current query and preserved spend data |
| Q6 – City spend ranks | 1,200 rows (0 RANK vs ROW_NUMBER ties) | 8 differences | Preserved spend values produce distinct ranks without ties |
| Q7 – Running daily revenue | 183 daily rows; final cumulative INR 41,822,667.48 | 183 days | Day count matches exactly; cumulative revenue reflects actual data |

For Q2, the highest city/category combination is Bengaluru / Home at INR 2,522,588.74.

The Pandas `pivot_table(..., margins=True)` grand total matches SQL Q2 at exactly INR 41,822,667.48.

---

# Part B

## RFM Segmentation & Lapse Prediction

The results below are the authoritative measured results produced on the corrected SQLite database. `archive/part_b_final/` preserves the validated Part B source and output files, sealed by `SHA256SUMS.txt`.

## RFM & Clustering Summary

RFM is evaluated as of 2025-10-01 across 1,200 customers.

- Recency (days): Median 13, Minimum 0, Maximum 134.
- Frequency (orders): Mean 9.525, Maximum 20.
- Monetary (INR): Mean INR 34,852.22, Maximum INR 98,372.83.

K-Means clustering was evaluated across K=2 through K=8 using standardized RFM features (`n_init=10`, `random_state=42`).

K=3 was selected based on the highest silhouette score (0.3497) and actionable profile separation.

## Customer Segments

| Segment | Customers | Mean Recency | Mean Frequency | Mean Monetary | Premium Count | Strategic Action |
|---|---:|---:|---:|---:|---:|---|
| Steady Shoppers | 581 | 12.68 days | 8.05 | INR 27,134.10 | 0 | Encourage cross-sells and regular repeat orders |
| At-Risk Shoppers | 178 | 52.18 days | 7.04 | INR 25,042.51 | 0 | Deploy win-back campaigns and investigate churn causes |
| High-Value Regulars | 441 | 12.24 days | 12.47 | INR 48,980.02 | 145 | Reward loyalty and protect with dedicated premium support |

## PCA Analysis

PCA reduces the three standardized RFM features to two principal components explaining 92.06% of total variance:

- PC1: 63.51%.
- PC2: 28.55%.

## Lapse Prediction & Modeling

**Cohort & Cutoff**

1,198 eligible customers with at least one completed order prior to 2025-09-01.

**Target Label**

- Active: At least one completed order occurred in [2025-09-01, 2025-10-01).
- Lapsed: Otherwise.

Results:

- Active: 949 (79.22%).
- Lapsed: 249 (20.78%).

**Leakage Prevention**

Features aggregate order records strictly before 2025-09-01. All transformers fit inside training folds via scikit-learn Pipeline.

**Train/Test Split**

Stratified 80/20 train/test split:

- Training: 958 customers.
- Testing: 240 customers.

## Model Evaluation

| Model | Test Accuracy | Precision | Recall | F1 Score | Specificity | False Positive Rate |
|---|---:|---:|---:|---:|---:|---:|
| Most-Frequent Baseline | 0.792 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| Logistic Regression (C=0.01) | 0.792 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| Random Forest (depth=3, leaf=5) | 0.792 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| Oversampled Logistic Regression | 0.542 | 0.237 | 0.540 | 0.329 | 0.542 | 0.458 |

**Key Insight**

Baseline, Logistic Regression, and Random Forest achieve 79.2% accuracy by predicting all customers active, detecting zero lapsed customers.

Training-only oversampling balances training classes from 759/199 to 759/759, raising lapse recall from 0.000 to 0.540 and detecting 27 of 50 test lapsed customers.

`outputs/retention_list.csv` contains the top-10 premium test customers prioritized for retention outreach.

---

# Part C

## Support Ticket Triage with Privacy & Safety Guardrails

Part C validates and triages the synthetic records in `data/raw/tickets.csv` using the offline `mock_llm.py` and strict regex-based PII masking.

## Data Quality

- Total records audited: 164.
- Duplicate rows: 0.
- Duplicate ticket IDs: 0.
- Empty messages: 14.
- Messages exceeding 400 tokens: 0.

Empty messages are retained and routed to Human Support Lead.

## PII Redaction

Masking covers:

- Email addresses (`[EMAIL]`).
- Indian and international mobile numbers (`[PHONE]`).
- Order IDs (`[ORDER_ID]`).

Contact-shaped patterns were detected across 22 affected rows and masked prior to LLM exposure and output generation.

## Classification & Guardrails

Only masked text is sent to `mock_llm.chat`.

A deterministic fraud safety override routes explicit security or unauthorized-purchase wording to Fraud/Security Team.

## Customer Enrichment

Tickets are enriched with Part B customer segment and premium status.

Missing lapse predictions remain unknown (0/164 coverage).

## Queue Allocations

| Support Queue | Tickets |
|---|---:|
| Billing Support | 49 |
| Technical Support | 34 |
| Fraud/Security Team | 34 |
| Delivery Support | 33 |
| Human Support Lead | 14 |

## Automated Tests

All 17 Part C unit tests pass.

---

# Part D

## Policy RAG & Refund Assessment Agent

Part D implements local lexical retrieval and a read-only refund assessment engine.

## Policy Retrieval

Policy text files in `data/policies/` are chunked and indexed via TF-IDF.

The assistant extracts exact source excerpts and validates grounding against retrieved chunks.

## Read-Only SQL Safety

Order queries use parameterized SQL on read-only SQLite connections.

Both `order_id` and verified matching `customer_id` are required. Default orders are never assumed.

## Refund Policy Rules

- Completed orders with delivery delay greater than 45 minutes are eligible for refund.
- Cancelled or pending orders are not refundable.
- Requests outside the 7-day completion window are denied.
- Large refunds greater than INR 1,000 require human approval.
- Handoff recommendations are flagged after 6 support turns or for fraud indicators.

## Assessment Safeguards

The engine outputs assessment recommendations to `outputs/refund_assessments.jsonl`.

Possible outcomes include:

- `REFUND_ELIGIBLE_NOT_EXECUTED`
- `CUSTOMER_VERIFICATION_REQUIRED`
- `NEEDS_REVIEW`

The system does not execute refunds, mutate financial ledgers, or send external notifications.

## Automated Tests

All 18 Part D unit tests pass.

---

# Limitations and Next Steps

## Known Limitations

**1. No Usable Completed-Delivery Measurements**

All 12,978 blank and 106 negative raw delivery times leave zero valid completed-order delivery measurements in the source data.

Delivery-time correlations are unavailable, and delivery-delay refund claims evaluate to `NEEDS_REVIEW`.

**2. Lapse Prediction Coverage**

Retention list outreach is restricted to the top-10 premium test cohort.

Missing predictions are left unknown, resulting in 0/164 coverage for the current support ticket cohort.

**3. Component Separation**

Part C (ticket triage) and Part D (refund agent) operate independently.

Part D does not consume Part C enriched tickets.

**4. Unverified Ticket-Contact Provenance**

Contact-shaped strings (email addresses and phone numbers) in `data/raw/tickets.csv` have unverified exact provenance.

They are masked before model processing.

See `reports/ticket_contact_provenance_and_sanitization.md`.

**5. Stateless Handoff Evaluation**

The policy's 6-step human handoff trigger is evaluated as an individual state threshold.

Full multi-turn conversational session tracking is not implemented.

**6. Local Simulation**

All LLM capabilities are simulated locally via `mock_llm.py` without external network API calls.

## Legacy and Archival Artifacts

| File | Classification | Status & Operational Role |
|---|---|---|
| `outputs/triage_results.csv` | Historical / Superseded | Early prototype output from initial commit (`e7f1eea`). Superseded by `outputs/ticket_triage.csv`. |
| `outputs/triage_budget_demo.csv` | Historical / Example | Test file demonstrating token budget exhaustion. Superseded by current error routing. |
| `outputs/agent_runs.jsonl` | Historical / Simulated | Multi-turn prototype agent execution log. Preserved for auditability; not live interactions. |
| `outputs/refund_ledger.jsonl` | Historical / Simulated | Simulated prototype ledger entries. Preserved for auditability; no real payouts occurred. |
| `archive/part_b_final/` | Authoritative Preservation Archive | Snapshot of Part B source code and outputs from the corrected SQLite database, sealed by `SHA256SUMS.txt`. |

## Next Steps

Potential future improvements include:

- Integrating Part C ticket context with Part D refund assessment workflows.
- Improving lapse prediction coverage for support-ticket customers.
- Adding usable delivery-time measurements when reliable source data becomes available.
- Implementing persistent multi-turn conversation state for escalation tracking.
- Extending automated test coverage across Parts A and B.

These are future improvements and are not represented as completed functionality in the current implementation.
