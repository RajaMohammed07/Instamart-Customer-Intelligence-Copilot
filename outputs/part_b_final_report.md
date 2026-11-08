# Part B Final Report — Authoritative Results

This report preserves the final Part B results produced from the corrected Part A database. These are the authoritative results for this project version.

## Part A database baseline

| Measure | Verified value |
|---|---:|
| Customers | 1,200 |
| Products | 40 |
| Unique orders | 12,309 |
| Completed orders | 11,430 |
| Cancelled orders | 217 |
| Pending orders | 662 |
| Completed revenue | INR 41,822,667.48 |
| Order dates | 2025-04-01 through 2025-09-30 |

## RFM analysis

| Measure | Result |
|---|---:|
| RFM customers | 1,200 |
| Recency median / minimum / maximum | 13 / 0 / 134 days |
| Frequency mean / maximum | 9.525 / 20 |
| Monetary mean / maximum | INR 34,852.22 / INR 98,372.83 |

RFM uses completed orders before the snapshot date, 2025-10-01.

## Customer segmentation

K-means tested K=2–8 using standardized RFM features, `n_init=10`, and `random_state=42`. The selected K is 3 with silhouette score 0.3497; it had the best observed silhouette among the tested values and produced interpretable customer profiles.

| PCA component | Explained variance |
|---|---:|
| PC1 | 63.51% |
| PC2 | 28.55% |
| Combined | 92.06% |

| Segment | Customers |
|---|---:|
| Steady Shoppers | 581 |
| At-Risk Shoppers | 178 |
| High-Value Regulars | 441 |
| Premium customers | 145 |

The premium-customer rule is monetary value at or above the 80th percentile, frequency at or above the median, and recency at or below the median.

## Lapse prediction

The cohort contains customers with at least one completed order before 2025-09-01. The outcome window is 2025-09-01 through 2025-09-30; active customers made a completed order during that window, and all other cohort customers are labeled lapsed.

| Measure | Result |
|---|---:|
| Pre-cutoff cohort | 1,198 |
| Active | 949 |
| Lapsed | 249 |
| Lapse rate | 20.78% |
| Train / test split | 958 / 240 |
| Test active | 190 |
| Test lapsed | 50 |

Confusion matrices use rows = actual `[active, lapsed]` and columns = predicted `[active, lapsed]`. The positive class is lapsed (1).

| Model | Confusion matrix | Accuracy | Precision | Recall | F1 | Specificity | FPR |
|---|---|---:|---:|---:|---:|---:|---:|
| Most-frequent baseline | `[[190,0],[50,0]]` | 0.792 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| Logistic regression | `[[190,0],[50,0]]` | 0.792 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| Random forest | `[[190,0],[50,0]]` | 0.792 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| Oversampled logistic regression | `[[103,87],[23,27]]` | 0.542 | 0.237 | 0.540 | 0.329 | 0.542 | 0.458 |

The unsampled models predicted no lapsed test customers. All grid-search candidates had zero mean five-fold F1. Logistic C=0.01 and random forest depth=3 / leaf=5 are first-in-grid ties, not proven optimal settings.

Training classes were oversampled from 759/199 to 759/759 using replacement. The 240-row test set remained unchanged. Oversampling improved recall but increased false positives. Accuracy alone does not adequately describe model performance.

## Leakage checks and limitations

- Features use pre-cutoff order history.
- September completed orders are used only for outcome labels.
- Preprocessing is fitted within cross-validation folds.
- Customer IDs are excluded from model features.
- Test data is not used for model selection.
- Oversampling is applied only to training data.
- Signup tenure is nonnegative.
- Age, city, and gender lack historical snapshots, so their values cannot be verified as of the cutoff.
- No usable completed-delivery measurements exist, so average delivery time could not be calculated as a feature.

Python compilation, output schema checks, model reload tests, and `git diff --check` passed. Assignment reference metrics were not forced; this report records the measured results above.
