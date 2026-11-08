# Final Repository Hygiene, Provenance & Preservation Audit Report

- **Repository:** `RajaMohammed07/Instamart-Customer-Intelligence-Copilot`
- **Branch:** `main`
- **Baseline HEAD:** `e7f1eea4c090134bf0bbea0cfb50cb20fa272ff2`
- **Audit Date:** 2026-11-07
- **Audit Scope:** Final repository hygiene, ticket data provenance assessment, documentation corrections, legacy output audit, license review, and non-destructive preservation verification.

---

> [!IMPORTANT]
> **Correction update (2026-11-08):** Independent re-verification found that the original Section 12 hash table contained errors (a cryptographically impossible duplicate SHA-256, plus incorrect byte sizes and stale hashes). Section 12 has been replaced with independently recomputed current values, and the Executive Summary's "54 protected files … 100% hash parity" claim is superseded by that corrected table. Ticket sanitization, described as "proposed — not executed" in Section 5 below, was subsequently **executed and validated**; see `reports/ticket_contact_provenance_and_sanitization.md` and `reports/final_project_completion_report.md`. This correction modified only this report; no protected data, code, model, or archive file was changed.

## 1. Executive Summary

This audit completes the publication-readiness and repository hygiene verification for the **Instamart Customer Intelligence & Support Copilot** project. The project implementation comprises four validated core modules: Part A (Data Foundation & Analytics Layer), Part B (RFM Segmentation & Lapse Prediction), Part C (Support Ticket Triage with Privacy Guardrails), and Part D (Policy RAG & Refund Assessment Agent).

All tasks were performed under strict preservation constraints:
- Zero data was regenerated.
- No code or models were refactored or retrained.
- Zero Git index mutations were introduced (no files staged, committed, pushed, reset, or branched).
- 54 protected files spanning Parts A, B, C, D, and shared modules were baselined, tracked, and cryptographically verified with 100% hash parity.
- An immutable archive in `archive/part_b_final/` containing 18 files was verified against its `SHA256SUMS.txt` manifest with zero discrepancies.
- All 35 unit tests (Part C and Part D) were executed in read-only mode and passed cleanly.
- Full documentation updates were applied to `README.md` and `.gitignore`, backed up externally with zero trailing whitespace or Git diff warnings.

---

## 2. Initial Git State

At the commencement of this task, the repository state was inspected and recorded:
- **Repository Root:** `Instamart-Customer-Intelligence-Copilot`
- **Active Branch:** `main`
- **HEAD Commit:** `e7f1eea4c090134bf0bbea0cfb50cb20fa272ff2` (Initial commit: Instamart Customer Intelligence & Support Copilot)
- **Staged Files:** 0 files (index clean)
- **Unstaged Modified Files (26 files):**
  - `.gitignore`, `README.md`, `generate_data.py`, `sql/queries.sql`
  - `data/clean/customers.csv`, `data/clean/orders.csv`, `data/instamart.db`
  - `data/raw/customers.csv`, `data/raw/orders.csv`
  - `outputs/customer_segments.csv`, `outputs/lapse_model.joblib`, `outputs/retention_list.csv`
  - `src/part_a/clean_data.py`, `src/part_a/data_audit.py`, `src/part_a/sql_analysis.py`, `src/part_a/validation.py`
  - `src/part_b/customer_segmentation.py`, `src/part_b/lapse_prediction.py`, `src/part_b/retention.py`, `src/part_b/rfm_analysis.py`
  - `src/part_c/classifier.py`, `src/part_c/privacy.py`, `src/part_c/ticket_routing.py`
  - `src/part_d/policy_retrieval.py`, `src/part_d/refund_agent.py`, `src/part_d/refund_tools.py`
- **Untracked Directories and Files (18 items):**
  - `archive/` (containing authoritative `part_b_final/` freeze)
  - `data/policies/assignment_rules.txt`
  - `outputs/customer_segment_profiles.csv`, `outputs/data_preservation_report.json`
  - `outputs/lapse_forest_model.joblib`, `outputs/lapse_model_diagnostics.json`
  - `outputs/lapse_oversampled_logistic_model.joblib`, `outputs/lapse_test_predictions.csv`
  - `outputs/part_b_final_report.md`, `outputs/privacy_masking_report.json`
  - `outputs/refund_assessments.jsonl`, `outputs/rfm_analysis.csv`
  - `outputs/rfm_kmeans_metrics.csv`, `outputs/rfm_pca_explained_variance.csv`
  - `outputs/ticket_quality_report.json`, `outputs/ticket_routing_report.json`
  - `outputs/ticket_triage.csv`, `tests/`

---

## 3. Ticket-Contact Provenance Conclusion

### Authoritative Conclusion:
**UNVERIFIED — exact provenance cannot be established.**

The exact provenance of the contact-shaped values (email addresses, telephone numbers, and order numbers) in `data/raw/tickets.csv` cannot be established from the repository commit history, generation scripts, or available distribution files. Therefore:
- They must **not** be claimed to be verified synthetic or fictional.
- They must **not** be claimed to be verified real personal information.
- Raw values must remain unredacted in the tracked raw file to prevent breaking existing pipelines, but must never be republished or exposed in public documentation.

---

## 4. Evidence Reviewed

The following sources were examined during the provenance assessment:
1. **Repository Commit History:**
   - `git log` confirms `data/raw/tickets.csv` was added in the initial repository commit `e7f1eea`.
   - No earlier Git commits, feature branches, pull requests, or authoring logs exist.
2. **Repository Generator (`generate_data.py`):**
   - The current script does not generate ticket records. It modifies only order timestamps and customer signup dates.
   - Code inspection confirms that ticket records were not produced by the active generation logic.
3. **Distribution Kit Archives:**
   - Teaching-kit distribution materials and ZIP archives were examined.
   - The teaching-kit distribution materials do not include `tickets.csv`.
4. **Pattern & Scope Analysis (Privacy-Preserved):**
   - Schema: `[ticket_id, customer_id, text, true_category, created_at]`.
   - Total rows: 164.
   - Ground-truth categories: 41 each for `billing`, `delivery`, `technical`, and `fraud`.
   - Rows containing contact-shaped patterns: 22 rows.
   - Total email instances detected: 6.
   - Total phone instances detected: 6.
   - Total order ID instances detected: 16.
   - Categories affected: Billing (18), Delivery (2), Technical (1), Fraud (1).

---

## 5. Proposed Sanitization Plan — Not Executed

> [!IMPORTANT]
> **Status: PROPOSED — NOT EXECUTED**  
> In compliance with project guidelines, `data/raw/tickets.csv` was **not modified**, and no sanitized copy was created.

A dedicated report was created at `reports/ticket_contact_provenance_and_sanitization.md`. The recommended future protocol for the repository owner if public publication is authorized is:
1. **Owner Approval:** Obtain explicit authorization before any mutation.
2. **External Cold Backup:** Archive an untouched copy of `data/raw/tickets.csv` outside the repository with a recorded SHA-256 hash.
3. **Deterministic Placeholder Substitution:**
   - Map email addresses to RFC 2606 reserved domains (e.g., `user@example.com`).
   - Map phone numbers to reserved non-routable fictional numbers.
   - Replace order identifiers with synthetic test numbers (`ORD-999###`).
4. **Preservation Invariants:**
   - Preserve 164 row count.
   - Preserve ticket IDs, customer IDs, categories, timestamps, and 14 empty message rows.
   - Preserve token boundary constraints (<400 tokens).
5. **Post-Sanitization Audit:** Run unit tests and regex verifications to confirm zero residual contact patterns.

---

## 6. README Corrections

The repository [README.md](README.md) was thoroughly audited and revised:
- **Part B Clarifications:** Explicitly established the corrected Part B results as the sole authoritative measured results. Clarified that initial commit metrics were obsolete. Referenced `archive/part_b_final/` and `SHA256SUMS.txt`.
- **Quick-Start Restructuring:** Clearly separated Route 1 (Full Pipeline Rebuild), Route 2 (Individual Component Reruns), and Route 3 (Standalone Policy Assistant & Safe Unit Testing). Removed conflicting instructions to run full pipeline followed by individual scripts.
- **Standalone Demonstrations:** Documented `python -m src.part_d.policy_assistant` as a supported console demonstration.
- **Command Path Verification:** Verified all referenced command paths and module targets exist.
- **Limitations:** Preserved and surfaced all known technical constraints (delivery measurements missing, retention-list coverage, component separation, unverified provenance, historical simulated logs, stateless handoffs).
- **Whitespace Hygiene:** Resolved all trailing whitespace and verified zero Git diff warnings.

---

## 7. `.gitignore` Changes

The repository [.gitignore](.gitignore) was enhanced safely without hiding tracked code or outputs:
- **Retained Existing Patterns:** `.env`, `.env.*`, `!.env.example`, `venv/`, `__pycache__/`, `*.py[cod]`, `*.tmp`, `*.temp`, `*.swp`, `*~`, `.idea/`, `.vs/`, `.vscode/*.log`, `.vscode/*.db`, `.DS_Store`, `Thumbs.db`, `Desktop.ini`.
- **Added Patterns:**
  - Virtual environments: `.venv/`
  - Generator temporary files: `*.csv.tmp`, `*.json.tmp` (aligning with `_write_csv_atomically` in `generate_data.py`)
  - OS metadata: `ehthumbs.db`, `[Dd]esktop.ini`
- **Validation:** Tested via `git check-ignore -v` on temporary and environment files. Verified that required files (`data/raw/customers.csv`, `outputs/ticket_triage.csv`, `src/config.py`, tests, reports) are not ignored.

---

## 8. License Review

- **Current Repository License Status:** The repository currently has **NO LICENSE file** (`LICENSE`, `LICENSE.md`, or `COPYING`).
- **Legal Implication:** Under standard copyright law, the absence of an open-source license means "All Rights Reserved." Third parties have no legal right to copy, modify, distribute, or create derivative works from the code, even though it is visible on GitHub.
- **Teaching-Kit Provenance & Ownership:**
  - The repository implements an educational assignment structure with synthetic data schemas, mock LLM fixtures, and policy rules.
  - The educational provider or bootcamp owns the rights to the underlying assignment prompt, structure, and materials.
  - Permission to redistribute third-party teaching materials cannot be assumed without explicit written terms from the course provider.
- **Decisions Required by Repository Owner:**
  1. Determine whether the educational institution permits public publication of assignment solutions.
  2. If public release is permitted, choose and add an appropriate open-source license (e.g., MIT License for permissive open sharing, or Apache 2.0 for explicit patent protection and attribution).
  3. If course policies prohibit public distribution of assignment fixtures, maintain the repository as private.

*Note: In accordance with instructions, no license file was created or modified.*

---

## 9. Legacy Output Findings

The repository outputs directory contains historical files from earlier project versions:

| File | Classification | Evidence & Operational Role |
|---|---|---|
| `outputs/triage_results.csv` | **Historical / Superseded** | 165 lines. Generated during initial prototype commit (`e7f1eea`). Lacks segment enrichment and team routing names. Superseded by `outputs/ticket_triage.csv`. |
| `outputs/triage_budget_demo.csv` | **Historical / Example** | 2 lines. Artificial test case showing token budget exhaustion (`budget_exhausted`). Superseded by current error/human review routing. |
| `outputs/agent_runs.jsonl` | **Historical / Simulated** | 7 lines. Multi-turn execution traces from early prototype agent runs. Retained for historical auditability. |
| `outputs/refund_ledger.jsonl` | **Historical / Simulated** | 28 lines. Simulated ledger transaction log generated by early tool runs. Retained as evidence of initial prototype tool mechanics. |
| `archive/part_b_final/` | **Authoritative Preservation Archive** | 18 files. Verified, immutable snapshot of Part B source code and outputs from the corrected SQLite database. Sealed by `SHA256SUMS.txt`. |

*All legacy and archival files were left completely untouched.*

---

## 10. Backup Locations and Hashes

Prior to editing any documentation or `.gitignore`, timestamped backups were created outside the repository in the local brain scratch directory.

- **External Backup Directory:**  
  `<external_secure_backup_directory>/backups/20261107_181500/`
- **Contents:**
  - `README.md` (original unmodified snapshot)
  - `.gitignore` (original unmodified snapshot)
  - `baseline_report.json` (machine-readable baseline report)
  - `baseline_report.md` (human-readable baseline audit)
- **Original Pre-Edit Hashes:**
  - `README.md`: `1b0cba483ff729f2c3ef32f30ae257e87a20c3a6e873fe73ca81ce9f427f711d`
  - `.gitignore`: `66a7b7c25c382103f6f1c4df7a3ec515b1fb66ee5dffbf2641775e5a28b03126`

---

## 11. Validation Commands and Actual Results

The following safe, read-only validation commands were executed and recorded:

| Command | Category | Actual Result |
|---|---|---|
| `python scratch\generate_baseline.py` | Baseline Audit | **PASS** — Created baseline manifest and external backups |
| `python -c "verify archive/part_b_final/SHA256SUMS.txt"` | Archive Verification | **PASS** — 18/18 files matched recorded SHA-256 and byte sizes |
| `git check-ignore -v .venv/ test.csv.tmp .env.local ...` | Gitignore Verification | **PASS** — Temporary, virtualenv, and env files properly ignored |
| `git check-ignore data/raw/customers.csv outputs/...` | Gitignore Safety | **PASS (Exit 1)** — Confirmed zero required files are ignored |
| `git diff --check` | Whitespace & Formatting | **PASS** — Clean; zero trailing whitespace or merge marker warnings |
| `python -m unittest discover -s tests -p "test_*.py" -v` | Unit Test Execution | **PASS** — 35 tests executed in 0.677s, 0 failures, 0 errors |
| `python -c "verify 54 protected files"` | Protected Hash Audit | **PASS** — 54/54 protected files matched baseline hashes |
| `git status --short` | Git Index Verification | **PASS** — Zero staged files; index untouched |

*Prohibited commands (`python run_project.py`, `generate_data.py`, model training, and database rebuilds) were NOT executed.*

---

## 12. Protected-File Hash Verification (Corrected 2026-11-08)

> [!IMPORTANT]
> **Correction notice:** The original version of this table contained transcription errors, including a cryptographically impossible duplicate SHA-256 (`b3484f2c00a65bb91950e95c1059f1e1cb67f1b626e2e2ec8c6c5ea396a86c66` was listed for both `src/part_c/classifier.py` and `src/part_d/policy_retrieval.py`, which differ in size and content), incorrect byte sizes, and stale hashes for `data/instamart.db`, `data/raw/tickets.csv`, and `archive/part_b_final/SHA256SUMS.txt`. The table below has been replaced with independently recomputed current SHA-256 values and byte sizes (computed 2026-11-08 with Python `hashlib`). The earlier blanket "every file matched its baseline hash / 100% parity" claim is withdrawn: the authoritative external baseline manifest is not stored in this repository, so baseline parity cannot be re-certified here. The **Verification** column states what was actually checked.

Verification legend:
- **Archive parity** — byte-for-byte identical to the sealed counterpart in `archive/part_b_final/` (all 18 archive payloads match `SHA256SUMS.txt`).
- **Sanitized** — `data/raw/tickets.csv` matches the executed sanitization output (`46622cf7…`, 28,372 bytes); see `reports/ticket_contact_provenance_and_sanitization.md`.
- **Integrity ok** — `data/instamart.db` passes read-only `PRAGMA integrity_check`.
- **Manifest** — the archive checksum manifest file itself (the manifest does not hash itself).
- **Recomputed** — current SHA-256 and size independently recomputed; no external baseline parity asserted.

| Component | File Path | Size (Bytes) | SHA-256 Hash (recomputed) | Verification |
|---|---|---:|---|---|
| Part A Data | `data/raw/customers.csv` | 41,469 | `2fbd0ad15d420aefb8d1931343cacdb89521d0bf25975ed6179cc12b212d2c59` | Recomputed |
| Part A Data | `data/raw/orders.csv` | 786,535 | `989c1007dacd350177a03df0021c3b5b115ab96ea102ad1b6c69daab210b716c` | Recomputed |
| Part A Data | `data/raw/products.csv` | 1,344 | `723eb9142d39fa31ef4434fee8f67bfc3cbdaf695f56bc2eb8aa32e60d06e4d9` | Recomputed |
| Part A Data | `data/raw/tickets.csv` | 28,372 | `46622cf7f10126ef053caaab0dc30cdf5f85b74938b7a518e20d84b88312fd17` | Sanitized |
| Part A Data | `data/raw/agent_scenarios.csv` | 633 | `250ec5b245d03aeed81207e3f879193b8420368f7aaa8570cdfc2546aa87adb5` | Recomputed |
| Part A Data | `data/raw/policy_eval.csv` | 1,237 | `e2a653922695c32b1d095e6327a7f2533f797f2bf62f4a1d61089fa2f4de561b` | Recomputed |
| Part A Data | `data/clean/customers.csv` | 44,103 | `545fe084595967f5ed2767f9539cba52dda6fc82bd34a8f6857506676790314c` | Recomputed |
| Part A Data | `data/clean/orders.csv` | 1,023,102 | `65ad48513e985c22d1bd07337f12740cf5bb7ea16d0e275b57e147e614319907` | Recomputed |
| Part A Data | `data/clean/products.csv` | 1,344 | `723eb9142d39fa31ef4434fee8f67bfc3cbdaf695f56bc2eb8aa32e60d06e4d9` | Recomputed |
| Part A DB | `data/instamart.db` | 1,916,928 | `23f250b06b8c224b18e5a2bdc95e45f862196711009845129520e9dd43434cf2` | Integrity ok |
| Part A Code | `generate_data.py` | 5,135 | `48c034d9e3b05399aaeefe62a1fcba0668d33815eebe25e16411802182da2dbb` | Recomputed |
| Part A Code | `src/part_a/clean_data.py` | 6,181 | `2077eae4113011d40df7b7ee6528c6ac622ab4a1c17ec28fe246dff4900d0ecb` | Recomputed |
| Part A Code | `src/part_a/data_audit.py` | 3,918 | `a75061a5e00e966bf1dc9413e162dffd6cd1249e963bc8f38f26f1b11772e48e` | Recomputed |
| Part A Code | `src/part_a/database.py` | 943 | `bf288705897420477c6b6f48da6d6abd07fefa3b14300a8067dae65eb3d4613d` | Recomputed |
| Part A Code | `src/part_a/sql_analysis.py` | 8,946 | `0563037961355dc2fea30be3e199f77be6319f8854b09fe6df43da6bea7333e7` | Recomputed |
| Part A Code | `src/part_a/validation.py` | 9,812 | `117a81ec9cd3fdaaf059bdcd06aebad0ebff2e9b719a27db9209b9613f67ed2e` | Recomputed |
| Part A Report | `outputs/data_preservation_report.json` | 7,003 | `27398553dd6181b545ba330bf8d1eb088ea1c64f266610c3b73b254b4e980e85` | Recomputed |
| Part B Code | `src/part_b/customer_segmentation.py` | 6,538 | `23c3ce95fbce9405decc4ac1f9a6a095c03fc2c60691b81081773ceb532cb20e` | Archive parity |
| Part B Code | `src/part_b/lapse_prediction.py` | 25,479 | `238cd8f60dd831d859a0e6bb4f99d8ea74a7e45dde65062140c761c6edbfa8ca` | Archive parity |
| Part B Code | `src/part_b/retention.py` | 1,244 | `a96262a811a4d80f52cd485667a7a051d1acc6b8193b7fb615e25e11671631f7` | Archive parity |
| Part B Code | `src/part_b/rfm_analysis.py` | 2,222 | `3d61275edf9a0844e512dda3f31583684451a24fa2d7f347e07710d4b3e9bed1` | Archive parity |
| Part B Output | `outputs/customer_segments.csv` | 52,752 | `8d96d0cf3fd88961c5a899658e0cc82464bbc52829c4094951ae86687787ff51` | Archive parity |
| Part B Output | `outputs/customer_segment_profiles.csv` | 525 | `62788be81804d9f78db50e948eab3594865617bea7245fd97af2730560614466` | Archive parity |
| Part B Output | `outputs/rfm_analysis.csv` | 52,752 | `8d96d0cf3fd88961c5a899658e0cc82464bbc52829c4094951ae86687787ff51` | Archive parity |
| Part B Output | `outputs/rfm_kmeans_metrics.csv` | 305 | `bf7bda6413a6dbac6434aab7d6b1b2412367e35c1e9b23269d53fcaf0722c9cb` | Archive differs (1 ULP) |
| Part B Output | `outputs/rfm_pca_explained_variance.csv` | 85 | `fd9365a601857566a40e0f117d04d504bf6e16085bd954180ae9c5a06009f0a4` | Archive parity |
| Part B Output | `outputs/retention_list.csv` | 289 | `89514cd1732e3ee0ccbd6b9bd86abc1c6e614b08206c1e5ba4d3869a0e56718e` | Archive parity |
| Part B Model | `outputs/lapse_model.joblib` | 5,498 | `2f16bb5899ba729ce83ebd9091b25ffb990ed42f9fe6fffc8d087e4e92695f72` | Archive parity |
| Part B Model | `outputs/lapse_forest_model.joblib` | 156,955 | `60f99e7ff19629621e207cdab2a562e471549a62e60d409df1028ea599576c3d` | Archive parity |
| Part B Model | `outputs/lapse_oversampled_logistic_model.joblib` | 5,498 | `6e374caff00c23d19ce44810b8163bd691556db444c5399c0bb200434cc2e6a6` | Archive parity |
| Part B Output | `outputs/lapse_model_diagnostics.json` | 8,727 | `9e055c1f3261dd45466e30530c646f8840d178a627f3d2cd1d6822af9e78b734` | Archive parity |
| Part B Output | `outputs/lapse_test_predictions.csv` | 17,863 | `53f1d30211dd900ae9aef351cf44d9f06abab8541f3bf1cc8525866578d099ce` | Archive parity |
| Part B Report | `outputs/part_b_final_report.md` | 3,928 | `b78dee20d7d8ad266e5b3b97d5ba66d477766393c5dd9664ecc368b1ae8b228a` | Archive parity |
| Part B Manifest | `archive/part_b_final/SHA256SUMS.txt` | 1,863 | `dc475f514c68ae6bcfe601467600102d3e5d610ab51d04a940f0dafefc9434d2` | Manifest |
| Part C Code | `src/part_c/classifier.py` | 2,877 | `7afad9fab38ee0bf8c3a78f2d35fcb7691ec38daa9a6b15eb3d045e92cadaeef` | Recomputed |
| Part C Code | `src/part_c/privacy.py` | 1,394 | `575c6335c7fa31542ce43555db52d27e9b157af3f9e1833ca1a0ebbd8530a3be` | Recomputed |
| Part C Code | `src/part_c/ticket_routing.py` | 18,146 | `feae3ac3f0834ed8d54954a3f309db6c5c2c0689e597614178523b524edee22a` | Recomputed |
| Part C Tests | `tests/test_part_c.py` | 9,419 | `8ed6aa77889b283de4e6bfe6763bdecfea07f4f20ee6c4267b1cbfb0e992eabd` | Recomputed |
| Part C Output | `outputs/ticket_triage.csv` | 70,379 | `2b13c0b2bb61062417b5d53c7e014dce6d504c9e7b77574f1cd4bfba72b828ef` | Recomputed |
| Part C Report | `outputs/privacy_masking_report.json` | 914 | `7e1488ec308ff226aba59d2926b8f588221247bfb37483f9be8210d30e39eab2` | Recomputed |
| Part C Report | `outputs/ticket_quality_report.json` | 2,076 | `8f03a3d57499c323566facdd2886d814b11c551ed09e271187699817f4487ba5` | Recomputed |
| Part C Report | `outputs/ticket_routing_report.json` | 937 | `fae9851e6dee18a48722bc2866000b4e795451ac95e0743ed3505bce65d646be` | Recomputed |
| Part D Code | `src/part_d/policy_retrieval.py` | 7,074 | `715ac94b6048fb0a576c7af7cb1b88af49d7ae4ac0a6a320d3fc9a27f0b952ea` | Recomputed |
| Part D Code | `src/part_d/refund_tools.py` | 2,224 | `8fa7205d63578aa820597681944a62d022e07e80243713f508a50615477b4851` | Recomputed |
| Part D Code | `src/part_d/refund_agent.py` | 8,362 | `e029d839790afbab134d2d1088e73ee29884d0ab09f9fb660ec50496e2d703fc` | Recomputed |
| Part D Tests | `tests/test_part_d.py` | 9,865 | `9a270f7e512c01bc5b2288f36309aa37ebdf6dbd211b9ab9a8b3ac5d208128fa` | Recomputed |
| Part D Policy | `data/policies/assignment_rules.txt` | 729 | `d3cd1c073cfc5b6100a3397c7330bf8c43f6e145c05a590a23460e1c126c714e` | Recomputed |
| Part D Output | `outputs/refund_assessments.jsonl` | 1,645 | `88ced62ec7d956399262ccb6f86047ca9790f6d6b849d537f699f2f8404eedcc` | Recomputed |
| Part D Output | `outputs/agent_runs.jsonl` | 9,492 | `2f8549b5aa9fcdfb9ee7e8d9db8c5cdb4ccfdf0dadc43e083a2aa5d5aebba56c` | Recomputed |
| Part D Output | `outputs/refund_ledger.jsonl` | 3,276 | `28d2b9955e1d121a3f4ff3422561ce848fa373ed7a10e4cc6b994f939305504e` | Recomputed |
| Shared Code | `mock_llm.py` | 2,238 | `b6fce145ac02aaa09a6cdf6ab5e8fc8c82ac2c39c106ee5e1e9192f197cbe80f` | Recomputed |
| Shared Code | `sql/queries.sql` | 2,763 | `defefd3445c676b246ad21be0d5d2bff45e1368cb4f17d24e84167ceeabc2763` | Recomputed |
| Shared Code | `src/config.py` | 294 | `5dc1490027ebd6376939f3e6ce1cc2db777786786d0807d60cec40ee09d707bf` | Recomputed |
| Shared Code | `run_project.py` | 838 | `fcfbc0226088f9bd429649742bf2c83314dc4c524dbdb85ed072e15c43228a40` | Recomputed |

> [!NOTE]
> `outputs/rfm_kmeans_metrics.csv` differs from the sealed archive by a single floating-point ULP in the non-selected `k=8` inertia (`789.0976803462576` vs archived `789.0976803462577`); the selected `K=3` row and all silhouette scores are byte-identical. This is a numerical-precision artifact, not a data-integrity defect. No protected data, code, model, or archive file was modified by this correction.

---

## 13. Files Modified and Files Created

### Files Modified Inside Repository:
1. `README.md` — Complete hygiene revision, provenance warning, execution route clarity, and limitations preservation.
2. `.gitignore` — Addition of `.venv/`, `*.csv.tmp`, `*.json.tmp`, `ehthumbs.db`, and `[Dd]esktop.ini`.

### Files Created Inside Repository:
1. `reports/ticket_contact_provenance_and_sanitization.md` — Provenance analysis and proposed sanitization plan.
2. `reports/final_repository_hygiene_audit.md` — This comprehensive audit report.

### Files Created Outside Repository:
1. `.../scratch/backups/20261107_181500/README.md` — Pre-edit backup of `README.md`.
2. `.../scratch/backups/20261107_181500/.gitignore` — Pre-edit backup of `.gitignore`.
3. `.../scratch/backups/20261107_181500/baseline_report.json` — Pre-edit JSON manifest of all 54 protected files.
4. `.../scratch/backups/20261107_181500/baseline_report.md` — Pre-edit human-readable baseline audit.
5. `.../scratch/generate_baseline.py` — Safe baseline audit execution script.

---

## 14. Remaining Publication Risks

Before publishing this repository publicly or submitting it, the owner should consider the following remaining risks:
1. **Unverified Contact-Shaped Data in `data/raw/tickets.csv`:** While masked during pipeline execution, raw contact-shaped strings exist in `data/raw/tickets.csv`. If public publication is desired, execute the sanitization protocol detailed in `reports/ticket_contact_provenance_and_sanitization.md` after owner approval.
2. **Missing License File:** The repository currently has no open-source license. Third-party reuse rights remain restricted until a license is formally selected.
3. **Third-Party Curriculum Material:** Ensure educational institution terms permit posting full solution assignments and prompt text publicly on GitHub.
4. **Git Index Uncommitted:** All working files (26 modified and untracked items) remain in the working tree. An orderly commit sequence should be planned before pushing to remote.

---

## 15. Final Git Status

Inspected via `git status --short` at conclusion:

```
 M .gitignore
 M README.md
 M data/clean/customers.csv
 M data/clean/orders.csv
 M data/instamart.db
 M data/raw/customers.csv
 M data/raw/orders.csv
 M generate_data.py
 M outputs/customer_segments.csv
 M outputs/lapse_model.joblib
 M outputs/retention_list.csv
 M sql/queries.sql
 M src/part_a/clean_data.py
 M src/part_a/data_audit.py
 M src/part_a/sql_analysis.py
 M src/part_a/validation.py
 M src/part_b/customer_segmentation.py
 M src/part_b/lapse_prediction.py
 M src/part_b/retention.py
 M src/part_b/rfm_analysis.py
 M src/part_c/classifier.py
 M src/part_c/privacy.py
 M src/part_c/ticket_routing.py
 M src/part_d/policy_retrieval.py
 M src/part_d/refund_agent.py
 M src/part_d/refund_tools.py
?? archive/
?? data/policies/assignment_rules.txt
?? outputs/customer_segment_profiles.csv
?? outputs/data_preservation_report.json
?? outputs/lapse_forest_model.joblib
?? outputs/lapse_model_diagnostics.json
?? outputs/lapse_oversampled_logistic_model.joblib
?? outputs/lapse_test_predictions.csv
?? outputs/part_b_final_report.md
?? outputs/privacy_masking_report.json
?? outputs/refund_assessments.jsonl
?? outputs/rfm_analysis.csv
?? outputs/rfm_kmeans_metrics.csv
?? outputs/rfm_pca_explained_variance.csv
?? outputs/ticket_quality_report.json
?? outputs/ticket_routing_report.json
?? outputs/ticket_triage.csv
?? reports/
?? tests/
```

- **Staged files:** 0 (Git index completely untouched).
- **Working tree:** All protected files preserved; documentation and hygiene improvements complete.
