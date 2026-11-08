# Ticket-Contact Data Provenance Assessment & Sanitization Report

## 1. Provenance Conclusion

**UNVERIFIED — exact provenance cannot be established.**

Based on exhaustive inspection of repository commit history, raw data files, and generation scripts:
- It cannot be established whether the original contact-shaped values (email addresses, phone numbers, and order numbers) in `data/raw/tickets.csv` were deterministically synthesized by an untracked external script or derived from external real-world samples.
- Consequently, they must **not** be claimed to be verified synthetic fixtures, nor claimed to be verified real personal data.
- In accordance with privacy governance principles, the raw contact-bearing strings have been sanitized in-place using deterministic fictional placeholders.

---

## 2. Evidence Reviewed

1. **Initial Repository Commit (`e7f1eea4c090134bf0bbea0cfb50cb20fa272ff2`)**:
   - `data/raw/tickets.csv` was added in the initial commit.
   - No earlier Git branches, authoring commits, or generation seeds exist in the repository.
2. **Repository Data Generator (`generate_data.py`)**:
   - The active script modifies only `signup_date` in `customers.csv` and `order_ts` in `orders.csv`.
   - It does not produce or alter `tickets.csv`.
3. **Teaching-Kit Distribution Artifacts**:
   - Teaching-kit distribution materials and ZIP archives were examined; the distribution archive does not include `tickets.csv`.
4. **Column & Pattern Scope**:
   - Schema: `[ticket_id, customer_id, text, true_category, created_at]`.
   - Total rows: exactly 164.
   - Contact values were confined strictly to the `text` column; zero contact values existed in `ticket_id`, `customer_id`, `true_category`, or `created_at`.

---

## 3. Scope of Affected Records

Prior to sanitization, a confidential, read-only regex audit detected contact-shaped patterns in **22 of 164 rows**:

| Metric | Measured Value |
|---|---:|
| Total rows | 164 |
| Affected rows (containing contact patterns) | 22 (13.4%) |
| Unaffected rows | 142 (86.6%) |
| Total email address instances | 6 |
| Total phone number instances | 6 |
| Total order ID instances | 16 |
| Preserved empty text messages | 14 |

### Breakdown of the 22 Affected Rows

| Row Index | Ticket ID | Customer ID | Category | Email Count | Phone Count | Order ID Count | Text Column Length |
|---:|---|---|---|---:|---:|---:|---:|
| 0 | `TK-001` | `C0001` | `billing` | 1 | 1 | 0 | 79 chars |
| 4 | `TK-005` | `C0005` | `billing` | 0 | 0 | 1 | 53 chars |
| 12 | `TK-013` | `C0013` | `billing` | 0 | 0 | 1 | 53 chars |
| 20 | `TK-021` | `C0021` | `billing` | 0 | 0 | 1 | 53 chars |
| 28 | `TK-029` | `C0029` | `billing` | 0 | 0 | 1 | 53 chars |
| 29 | `TK-030` | `C0030` | `delivery` | 1 | 1 | 0 | 79 chars |
| 36 | `TK-037` | `C0037` | `billing` | 0 | 0 | 1 | 53 chars |
| 52 | `TK-053` | `C0053` | `billing` | 0 | 0 | 1 | 53 chars |
| 58 | `TK-059` | `C0059` | `technical` | 1 | 1 | 0 | 79 chars |
| 60 | `TK-061` | `C0061` | `billing` | 0 | 0 | 1 | 53 chars |
| 76 | `TK-077` | `C0077` | `billing` | 0 | 0 | 1 | 53 chars |
| 84 | `TK-085` | `C0085` | `billing` | 0 | 0 | 1 | 53 chars |
| 87 | `TK-088` | `C0088` | `fraud` | 1 | 1 | 0 | 79 chars |
| 92 | `TK-093` | `C0093` | `billing` | 0 | 0 | 1 | 53 chars |
| 100 | `TK-101` | `C0101` | `billing` | 0 | 0 | 1 | 53 chars |
| 108 | `TK-109` | `C0109` | `billing` | 0 | 0 | 1 | 53 chars |
| 116 | `TK-117` | `C0117` | `billing` | 1 | 1 | 0 | 79 chars |
| 124 | `TK-125` | `C0125` | `billing` | 0 | 0 | 1 | 53 chars |
| 140 | `TK-141` | `C0141` | `billing` | 0 | 0 | 1 | 53 chars |
| 145 | `TK-146` | `C0146` | `delivery` | 1 | 1 | 0 | 79 chars |
| 148 | `TK-149` | `C0149` | `billing` | 0 | 0 | 1 | 53 chars |
| 156 | `TK-157` | `C0157` | `billing` | 0 | 0 | 1 | 53 chars |

---

## 4. Deterministic Sanitization Execution Evidence

> [!NOTE]
> **Status: EXECUTED & FULLY VALIDATED**  
> Authorized and executed on November 7, 2026.

### Pre-Modification External Cold Backup
Before in-place mutation, the original `data/raw/tickets.csv` was preserved in a timestamped external directory:
- **Backup File:** `<external_secure_backup_directory>/backups/sanitization_pre_20261107_183826/tickets.csv`
- **Original SHA-256:** `54dd41588aa3fcb4c3ac0de492bd57231477b76a4f730a71d0cf294d8c7285ab`
- **Original Byte Size:** 28,324 bytes

### Deterministic Replacements Applied
1. **Email Replacements (6 instances):**  
   Sequentially substituted with RFC 2606 reserved example domain placeholders:  
   `user001@example.com` through `user006@example.com`.
2. **Phone Number Replacements (6 instances):**  
   Sequentially substituted with reserved non-routable fictional numbers:  
   `+91-99999-00001` through `+91-99999-00006`.
3. **Order ID Replacements (16 instances):**  
   Sequentially substituted with synthetic test order identifiers:  
   `ORD-999001` through `ORD-999016`.

### Post-Sanitization File Metrics
- **File:** `data/raw/tickets.csv`
- **Post-Sanitization SHA-256:** `46622cf7f10126ef053caaab0dc30cdf5f85b74938b7a518e20d84b88312fd17`
- **Post-Sanitization Byte Size:** 28,372 bytes
- **Row Count:** Exactly 164 rows preserved.
- **Structural Integrity:** `ticket_id`, `customer_id`, `true_category`, `created_at`, and all 14 empty message rows are 100% identical to the original file.

---

## 5. Post-Execution Validation & Downstream Invariance

1. **PII Masking Equivalence Check ([PASS]):**  
   `redact_pii(original_text)` was evaluated against `redact_pii(sanitized_text)` across all 164 rows:
   - **Result:** **0 differences across all 164 rows.**
   - Because `redact_pii` maps both the original and fictional patterns to standard redaction tokens (`[EMAIL]`, `[PHONE]`, `[ORDER_ID]`), downstream triage categories, routing rules, and customer segment enrichments are mathematically invariant.
2. **Post-Sanitization Regex Audit ([PASS]):**  
   A regex scan of the sanitized `tickets.csv` confirmed that **zero unmasked non-fictional emails, phone numbers, or order IDs remain**.
3. **Automated Test Suite ([PASS]):**  
   All 35 unit tests (17 in `tests/test_part_c.py` and 18 in `tests/test_part_d.py`) pass cleanly in 0.613s.
4. **Protected File Integrity ([PASS]):**  
   All 53 untouched protected files matched their master baseline hashes with 100% cryptographic parity.
