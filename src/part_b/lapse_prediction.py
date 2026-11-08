from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils import resample

from src.config import OUTPUTS_DIR
from src.part_b.retention import generate_retention_list
from src.part_b.rfm_analysis import (
    compute_rfm,
    identify_premium_customers,
    load_part_b_data,
)

CUTOFF = pd.Timestamp("2025-09-01")
OUTCOME_END = CUTOFF + pd.DateOffset(months=1)
NUMERIC_FEATURES = [
    "recency",
    "frequency",
    "monetary",
    "avg_discount",
    "cancellation_rate",
    "age",
    "tenure_days",
]
CATEGORICAL_FEATURES = ["favourite_category", "city", "gender"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def build_lapse_dataset(
    orders: pd.DataFrame,
    customers: pd.DataFrame,
    cutoff: str = "2025-09-01",
) -> pd.DataFrame:
    """Build customer features before cutoff and labels in the following month."""
    cutoff_ts = pd.Timestamp(cutoff)
    outcome_end = cutoff_ts + pd.DateOffset(months=1)
    required_order_columns = {
        "customer_id",
        "order_id",
        "order_ts",
        "status",
        "order_amount",
        "discount_pct",
        "delivery_minutes",
        "category",
    }
    required_customer_columns = {
        "customer_id",
        "city",
        "age",
        "gender",
        "signup_date",
    }
    missing_orders = sorted(required_order_columns.difference(orders.columns))
    missing_customers = sorted(required_customer_columns.difference(customers.columns))
    if missing_orders or missing_customers:
        raise ValueError(
            "Part B source data is missing required columns: "
            f"orders={missing_orders}, customers={missing_customers}"
        )

    orders = orders.copy()
    customers = customers.copy()
    orders["order_ts"] = pd.to_datetime(orders["order_ts"], errors="raise")
    if orders["order_ts"].isna().any():
        raise ValueError("Part B cannot validate cutoff windows with null order_ts values.")

    pre_cutoff = orders.loc[orders["order_ts"].lt(cutoff_ts)].copy()
    if not pre_cutoff["order_ts"].lt(cutoff_ts).all():
        raise AssertionError("A feature order falls on or after the cutoff.")
    completed_pre = pre_cutoff.loc[pre_cutoff["status"].eq("completed")].copy()
    completed_pre["order_ts"] = pd.to_datetime(completed_pre["order_ts"])
    cohort_ids = completed_pre["customer_id"].drop_duplicates()
    if cohort_ids.empty:
        raise ValueError("The pre-cutoff completed-order cohort is empty.")

    completed_features = completed_pre.groupby("customer_id").agg(
        recency=("order_ts", lambda values: (cutoff_ts - values.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("order_amount", "sum"),
    )
    feature_orders = pre_cutoff.loc[
        pre_cutoff["status"].astype("string").str.lower().ne("pending")
    ].copy()
    pre_cutoff_features = feature_orders.groupby("customer_id").agg(
        avg_discount=("discount_pct", "mean"),
        cancellation_rate=(
            "status",
            lambda values: values.eq("cancelled").mean(),
        ),
    )
    favourite_category = completed_pre.groupby("customer_id")["category"].agg(
        lambda values: (
            values.mode().iloc[0]
            if not values.mode().empty
            else "Unknown"
        )
    )

    features = completed_features.join(pre_cutoff_features, how="left")
    features["favourite_category"] = favourite_category
    features = features.reset_index().merge(
        customers[list(required_customer_columns)],
        on="customer_id",
        how="left",
        validate="one_to_one",
    )
    signup_ts = pd.to_datetime(features.pop("signup_date"), errors="raise")
    tenure_days = (cutoff_ts - signup_ts).dt.days.astype(float)
    # Future or inconsistent signup dates cannot be used as pre-cutoff tenure.
    tenure_days.loc[signup_ts.ge(cutoff_ts)] = np.nan
    features["tenure_days"] = tenure_days

    if not feature_orders["order_ts"].lt(cutoff_ts).all():
        raise AssertionError("A model feature order is on or after the cutoff.")
    outcome_orders = orders.loc[
        orders["status"].eq("completed")
        & orders["order_ts"].ge(cutoff_ts)
        & orders["order_ts"].lt(outcome_end)
    ]
    if not (
        outcome_orders["order_ts"].ge(cutoff_ts)
        & outcome_orders["order_ts"].lt(outcome_end)
    ).all():
        raise AssertionError("An outcome order falls outside the lapse window.")
    if set(features["customer_id"]) != set(cohort_ids):
        raise AssertionError(
            "The lapse dataset does not match the completed-order cohort."
        )
    active_ids = set(outcome_orders["customer_id"])
    features["lapsed"] = (~features["customer_id"].isin(active_ids)).astype(int)
    features.attrs["cutoff"] = cutoff_ts
    features.attrs["outcome_end"] = outcome_end
    features.attrs["latest_feature_order"] = feature_orders["order_ts"].max()
    features.attrs["earliest_feature_order"] = feature_orders["order_ts"].min()
    features.attrs["cohort_size"] = len(cohort_ids)
    features.attrs["outcome_order_count"] = len(outcome_orders)
    features.attrs["future_signup_count"] = int(signup_ts.ge(cutoff_ts).sum())
    features.attrs["feature_customer_ids"] = set(features["customer_id"])
    features.attrs["outcome_customer_ids"] = set(outcome_orders["customer_id"])
    return features[["customer_id", *FEATURES, "lapsed"]]


def _make_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                NUMERIC_FEATURES,
            ),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "onehot",
                            OneHotEncoder(drop="first", handle_unknown="ignore"),
                        ),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ]
    )


def _metrics(y_true: pd.Series, predictions: np.ndarray) -> dict:
    matrix = confusion_matrix(y_true, predictions, labels=[0, 1])
    true_negative, false_positive = matrix[0]
    false_negative, true_positive = matrix[1]
    total = int(matrix.sum())
    return {
        "confusion_matrix": matrix.tolist(),
        "accuracy": float((true_negative + true_positive) / total),
        "precision": float(
            precision_score(y_true, predictions, pos_label=1, zero_division=0)
        ),
        "recall": float(
            recall_score(y_true, predictions, pos_label=1, zero_division=0)
        ),
        "f1": float(f1_score(y_true, predictions, pos_label=1, zero_division=0)),
        "specificity": float(
            true_negative / (true_negative + false_positive)
            if true_negative + false_positive
            else 0.0
        ),
        "false_positive_rate": float(
            false_positive / (false_positive + true_negative)
            if false_positive + true_negative
            else 0.0
        ),
    }


def _print_metrics(name: str, scores: dict) -> None:
    print(
        f"{name}: confusion_matrix={scores['confusion_matrix']}, "
        f"accuracy={scores['accuracy']:.3f}, "
        f"precision={scores['precision']:.3f}, "
        f"recall={scores['recall']:.3f}, f1={scores['f1']:.3f}, "
        f"specificity={scores['specificity']:.3f}, "
        f"false_positive_rate={scores['false_positive_rate']:.3f}"
    )


def _positive_probability(model: Pipeline, features: pd.DataFrame) -> np.ndarray:
    positive_index = int(np.flatnonzero(model.classes_ == 1)[0])
    return model.predict_proba(features)[:, positive_index]


def _grid_search_diagnostics(search: GridSearchCV) -> list[dict]:
    return [
        {
            "params": {
                name: value.item() if isinstance(value, np.generic) else value
                for name, value in params.items()
            },
            "fold_f1_scores": [
                float(search.cv_results_[f"split{split}_test_score"][index])
                for split in range(search.n_splits_)
            ],
            "mean_cv_f1": float(search.cv_results_["mean_test_score"][index]),
            "std_cv_f1": float(search.cv_results_["std_test_score"][index]),
            "rank": int(search.cv_results_["rank_test_score"][index]),
        }
        for index, params in enumerate(search.cv_results_["params"])
    ]


def _oversample_training_data(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> tuple[pd.DataFrame, pd.Series]:
    training = X_train.copy()
    training["_target"] = y_train.to_numpy()
    class_counts = y_train.value_counts()
    majority_count = int(class_counts.max())
    balanced = [
        resample(
            training.loc[training["_target"].eq(class_value)],
            replace=True,
            n_samples=majority_count,
            random_state=42,
        )
        for class_value in sorted(class_counts.index)
    ]
    oversampled = pd.concat(balanced).sample(frac=1, random_state=42)
    return oversampled.drop(columns="_target"), oversampled["_target"].astype(int)


def _clear_invalid_model_outputs() -> None:
    for path in (
        OUTPUTS_DIR / "lapse_model.joblib",
        OUTPUTS_DIR / "retention_list.csv",
    ):
        if path.exists():
            path.unlink()
            print(f"Removed stale Part B output that cannot be validated: {path}")


def _print_feature_interpretation(logistic_pipeline: Pipeline, forest_pipeline: Pipeline):
    preprocessor = logistic_pipeline.named_steps["preprocess"]
    feature_names = preprocessor.get_feature_names_out()
    coefficients = logistic_pipeline.named_steps["model"].coef_[0]
    coefficient_table = pd.DataFrame(
        {"feature": feature_names, "coefficient": coefficients}
    ).sort_values("coefficient")
    print(
        "\nLogistic-regression coefficients (negative means lower predicted lapse "
        "odds; positive means higher odds, holding other features constant):"
    )
    print("Most negative:\n", coefficient_table.head(8).to_string(index=False))
    print("Most positive:\n", coefficient_table.tail(8).iloc[::-1].to_string(index=False))

    forest_importances = forest_pipeline.named_steps["model"].feature_importances_
    importance_table = pd.DataFrame(
        {"feature": feature_names, "importance": forest_importances}
    ).sort_values("importance", ascending=False)
    print("\nRandom-forest feature importances (relative split contribution):")
    print(importance_table.head(10).to_string(index=False))


def run_lapse_model(
    orders: pd.DataFrame | None = None,
    customers: pd.DataFrame | None = None,
    segments: pd.DataFrame | None = None,
):
    if orders is None or customers is None:
        orders, customers = load_part_b_data()
    data = build_lapse_dataset(orders, customers, cutoff=str(CUTOFF.date()))
    missing_features = sorted(set(FEATURES).difference(data.columns))
    if missing_features:
        raise ValueError(f"Required model features are missing: {missing_features}")

    counts = data["lapsed"].value_counts().sort_index()
    lapsed_count = int(counts.get(1, 0))
    active_count = int(counts.get(0, 0))
    print("\nLeakage-free lapse cohort validation:")
    print(f"Cutoff: {CUTOFF.date()} (features use order timestamps strictly before cutoff)")
    print(f"Outcome window: [{CUTOFF.date()}, {OUTCOME_END.date()})")
    print(
        f"Cohort customers: {len(data)}; active in outcome window: {active_count}; "
        f"lapsed: {lapsed_count}; lapse rate: {lapsed_count / len(data):.2%}"
    )
    print(
        f"Latest feature order: {data.attrs['latest_feature_order']}; "
        f"completed outcome-window orders: {data.attrs['outcome_order_count']}"
    )
    print(
        "Feature leakage check: no customer/order timestamps or outcome-window "
        "records are model features."
    )
    print(f"Required features present: {len(FEATURES)}/{len(FEATURES)}.")
    print(
        "Unavailable pre-cutoff tenure values from signup dates on/after cutoff: "
        f"{data.attrs['future_signup_count']} (left missing for training-only imputation)."
    )

    if data["lapsed"].nunique() != 2:
        print(
            "Cannot train or evaluate a lapse classifier: the observed cohort has "
            f"only outcome class(es) {counts.to_dict()}. Both lapsed and active "
            "customers are required; no labels will be synthesized."
        )
        _clear_invalid_model_outputs()
        return None

    X = data[FEATURES].copy()
    y = data["lapsed"].copy()
    customer_ids = data["customer_id"].to_numpy()
    X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(
        X,
        y,
        customer_ids,
        test_size=0.2,
        stratify=y,
        random_state=42,
    )
    if set(ids_train).intersection(ids_test):
        raise AssertionError("Train/test customer overlap detected.")
    print(
        f"Train/test separation: {len(ids_train)}/{len(ids_test)} customers; "
        f"overlap={len(set(ids_train).intersection(ids_test))}."
    )
    training_class_counts = y_train.value_counts()
    if int(training_class_counts.min()) < 5:
        raise ValueError(
            "Five-fold stratified cross-validation requires at least five training "
            f"examples per outcome class; got {training_class_counts.to_dict()}."
        )

    baseline = DummyClassifier(strategy="most_frequent")
    baseline.fit(X_train, y_train)
    baseline_predictions = baseline.predict(X_test)
    baseline_probabilities = _positive_probability(baseline, X_test)
    baseline_scores = _metrics(y_test, baseline_predictions)
    _print_metrics("Baseline (most frequent class)", baseline_scores)

    logistic_pipeline = Pipeline(
        steps=[
            ("preprocess", _make_preprocessor()),
            ("model", LogisticRegression(max_iter=1000)),
        ]
    )
    logistic_search = GridSearchCV(
        logistic_pipeline,
        param_grid={"model__C": [0.01, 0.1, 1, 10, 100]},
        cv=5,
        scoring="f1",
        n_jobs=None,
    )
    logistic_search.fit(X_train, y_train)
    best_logistic = logistic_search.best_estimator_
    logistic_predictions = best_logistic.predict(X_test)
    logistic_probabilities = _positive_probability(best_logistic, X_test)
    logistic_scores = _metrics(y_test, logistic_predictions)
    print(f"Logistic best C: {logistic_search.best_params_['model__C']}")
    _print_metrics("Logistic regression", logistic_scores)

    forest_pipeline = Pipeline(
        steps=[
            ("preprocess", _make_preprocessor()),
            (
                "model",
                RandomForestClassifier(n_estimators=100, random_state=42),
            ),
        ]
    )
    forest_search = GridSearchCV(
        forest_pipeline,
        param_grid={
            "model__max_depth": [3, 5, 8],
            "model__min_samples_leaf": [5, 10, 20],
        },
        cv=5,
        scoring="f1",
        n_jobs=None,
    )
    forest_search.fit(X_train, y_train)
    best_forest = forest_search.best_estimator_
    forest_predictions = best_forest.predict(X_test)
    forest_probabilities = _positive_probability(best_forest, X_test)
    forest_scores = _metrics(y_test, forest_predictions)
    print(f"Random-forest best parameters: {forest_search.best_params_}")
    _print_metrics("Random forest", forest_scores)

    X_over, y_over = _oversample_training_data(X_train, y_train)
    oversampled_logistic = clone(best_logistic)
    oversampled_logistic.fit(X_over, y_over)
    oversampled_predictions = oversampled_logistic.predict(X_test)
    oversampled_probabilities = _positive_probability(oversampled_logistic, X_test)
    oversampled_scores = _metrics(y_test, oversampled_predictions)
    oversampling_before = {
        str(label): int(count)
        for label, count in y_train.value_counts().sort_index().items()
    }
    oversampling_after = {
        str(label): int(count)
        for label, count in y_over.value_counts().sort_index().items()
    }
    print(
        f"\nTraining-only oversampling: {len(X_train)} -> {len(X_over)} rows "
        "(replacement=True, random_state=42); test set unchanged."
    )
    _print_metrics("Logistic regression after oversampling", oversampled_scores)
    print(
        "Oversampling change: "
        f"precision {logistic_scores['precision']:.3f} -> "
        f"{oversampled_scores['precision']:.3f}; recall "
        f"{logistic_scores['recall']:.3f} -> {oversampled_scores['recall']:.3f}."
    )
    print(
        "Beginner guide: each confusion-matrix row is the true class (not lapsed, "
        "then lapsed) and each column is the model prediction. Precision measures "
        "how many customers flagged as lapsed really lapsed; recall measures how "
        "many of all lapsed customers were found; F1 balances the two. Accuracy "
        "alone can look high when most customers belong to one class, even if the "
        "model misses nearly all lapsed customers."
    )
    _print_feature_interpretation(best_logistic, best_forest)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    model_paths = {
        "logistic_regression": OUTPUTS_DIR / "lapse_model.joblib",
        "random_forest": OUTPUTS_DIR / "lapse_forest_model.joblib",
        "oversampled_logistic": OUTPUTS_DIR / "lapse_oversampled_logistic_model.joblib",
    }
    models = {
        "logistic_regression": best_logistic,
        "random_forest": best_forest,
        "oversampled_logistic": oversampled_logistic,
    }
    for model_name, model in models.items():
        joblib.dump(model, model_paths[model_name])
        reloaded = joblib.load(model_paths[model_name])
        if not np.array_equal(reloaded.predict(X_test), model.predict(X_test)):
            raise AssertionError(f"Reloaded {model_name} predictions do not match.")
    print("Saved and reloaded all selected models; predictions verified.")

    predictions_path = OUTPUTS_DIR / "lapse_test_predictions.csv"
    pd.DataFrame(
        {
            "actual_lapsed": y_test.to_numpy(),
            "baseline_prediction": baseline_predictions,
            "baseline_lapse_probability": baseline_probabilities,
            "logistic_prediction": logistic_predictions,
            "logistic_lapse_probability": logistic_probabilities,
            "random_forest_prediction": forest_predictions,
            "random_forest_lapse_probability": forest_probabilities,
            "oversampled_logistic_prediction": oversampled_predictions,
            "oversampled_logistic_lapse_probability": oversampled_probabilities,
        }
    ).to_csv(predictions_path, index=False)
    diagnostics_path = OUTPUTS_DIR / "lapse_model_diagnostics.json"
    diagnostics = {
        "cutoff": CUTOFF.date().isoformat(),
        "outcome_window": {
            "start_inclusive": CUTOFF.date().isoformat(),
            "end_exclusive": OUTCOME_END.date().isoformat(),
        },
        "positive_class": {"value": 1, "meaning": "lapsed"},
        "confusion_matrix_orientation": {
            "rows": ["actual_not_lapsed_0", "actual_lapsed_1"],
            "columns": ["predicted_not_lapsed_0", "predicted_lapsed_1"],
        },
        "split": {
            "random_state": 42,
            "test_size": 0.2,
            "stratified": True,
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "train_class_counts": oversampling_before,
            "test_class_counts": {
                str(label): int(count)
                for label, count in y_test.value_counts().sort_index().items()
            },
        },
        "logistic_regression": {
            "cv_folds": logistic_search.n_splits_,
            "scoring": logistic_search.scoring,
            "candidate_C_values": [0.01, 0.1, 1, 10, 100],
            "best_params": logistic_search.best_params_,
            "best_cv_f1": float(logistic_search.best_score_),
            "cv_results": _grid_search_diagnostics(logistic_search),
            "test_metrics": logistic_scores,
        },
        "random_forest": {
            "cv_folds": forest_search.n_splits_,
            "scoring": forest_search.scoring,
            "candidate_max_depth": [3, 5, 8],
            "candidate_min_samples_leaf": [5, 10, 20],
            "best_params": forest_search.best_params_,
            "best_cv_f1": float(forest_search.best_score_),
            "cv_results": _grid_search_diagnostics(forest_search),
            "test_metrics": forest_scores,
        },
        "baseline": {"test_metrics": baseline_scores},
        "feature_audit": {
            "feature_columns": FEATURES,
            "customer_id_in_features": False,
            "feature_order_min": str(data.attrs["earliest_feature_order"]),
            "feature_order_max": str(data.attrs["latest_feature_order"]),
            "feature_cutoff_exclusive": CUTOFF.isoformat(),
            "outcome_order_count": int(data.attrs["outcome_order_count"]),
            "outcome_window_start_inclusive": CUTOFF.isoformat(),
            "outcome_window_end_exclusive": OUTCOME_END.isoformat(),
            "signup_tenure_negative_count": int((data["tenure_days"].dropna() < 0).sum()),
            "signup_tenure_missing_count": int(data["tenure_days"].isna().sum()),
            "future_signup_count": int(data.attrs["future_signup_count"]),
            "historical_attribute_limitations": (
                "Age, city, and gender are static generated attributes without "
                "historical snapshots and are not verified as-of the cutoff."
            ),
            "preprocessing_fit": "ColumnTransformer is inside the GridSearchCV pipeline; each CV fold fits on its training fold.",
            "test_data_used_for_model_selection": False,
        },
        "model_files": {name: path.name for name, path in model_paths.items()},
        "oversampling": {
            "training_only": True,
            "replacement": True,
            "random_state": 42,
            "before_class_counts": oversampling_before,
            "after_class_counts": oversampling_after,
            "original_test_rows": len(X_test),
            "test_rows_after_sampling": len(X_test),
            "test_metrics": oversampled_scores,
            "test_set_modified": False,
        },
        "test_predictions_file": predictions_path.name,
        "customer_identifiers_in_diagnostics": False,
    }
    with diagnostics_path.open("w", encoding="utf-8") as diagnostics_file:
        json.dump(diagnostics, diagnostics_file, indent=2)
        diagnostics_file.write("\n")
    print(f"Saved model audit diagnostics to {diagnostics_path}.")

    if segments is None:
        rfm = compute_rfm(orders, customers)
        segments = rfm.copy()
        segments["is_premium"] = identify_premium_customers(segments).astype(int)
    premium_ids = set(
        segments.loc[segments["is_premium"].eq(1), "customer_id"]
    )
    premium_test_ids = set(ids_test).intersection(premium_ids)
    if not premium_test_ids:
        retention = pd.DataFrame(columns=["customer_id", "lapse_probability"])
    else:
        retention = generate_retention_list(
            reloaded,
            X_test,
            y_test,
            customer_ids=ids_test,
            premium_customer_ids=premium_ids,
        )[["customer_id", "lapse_probability"]]
    retention.to_csv(OUTPUTS_DIR / "retention_list.csv", index=False)
    print(
        f"Saved top {len(retention)} premium test customers to "
        f"{OUTPUTS_DIR / 'retention_list.csv'}."
    )
    return {
        "model": best_logistic,
        "logistic_search": logistic_search,
        "forest_search": forest_search,
        "metrics": {
            "baseline": baseline_scores,
            "logistic": logistic_scores,
            "random_forest": forest_scores,
            "oversampled_logistic": oversampled_scores,
        },
    }


def main():
    run_lapse_model()


if __name__ == "__main__":
    main()
