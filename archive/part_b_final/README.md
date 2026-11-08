# Archived Part B — Authoritative Final Version

This archive preserves the authoritative Part B implementation and results generated using the corrected Part A database. Archive creation was performed without running or regenerating Parts A, B, C, or D.

The archived results are the authoritative Part B results from the corrected Part A database. Earlier Part B metrics from the superseded dataset are obsolete, and earlier model outputs must not be reused. Any future Part B rerun must be treated as a new version and must not silently replace this archive.

## Contents

- `outputs/part_b_final_report.md` — standalone final report of the measured baseline, RFM, segmentation, lapse-model metrics, leakage checks, and limitations.
- `src/part_b/` — all current Part B Python source files.
- `outputs/` — all current Part B outputs:
  - `rfm_analysis.csv`
  - `customer_segments.csv`
  - `rfm_kmeans_metrics.csv`
  - `customer_segment_profiles.csv`
  - `rfm_pca_explained_variance.csv`
  - `lapse_model.joblib`
  - `lapse_forest_model.joblib`
  - `lapse_oversampled_logistic_model.joblib`
  - `lapse_model_diagnostics.json`
  - `lapse_test_predictions.csv`
  - `retention_list.csv`
- `SHA256SUMS.txt` — SHA-256 and byte-size manifest for every archived payload file, including this README and the archived report. The manifest does not hash itself.

The diagnostics and test prediction outputs are the retained model-evaluation evidence. The report records that Python compilation, output schema checks, model reload tests, and `git diff --check` passed during the validated Part B rebuild. No Part B rerun or model retraining was performed to create this archive.

## Archive provenance

- Repository branch at preservation: `main`
- HEAD at preservation: `e7f1eea4c090134bf0bbea0cfb50cb20fa272ff2`
- Source working files remain in their original project locations. This archive is a separate preserved copy.
