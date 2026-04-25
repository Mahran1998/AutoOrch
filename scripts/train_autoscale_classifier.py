from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from autoorch.features import FEATURES


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="experiments/dataset_autoscale.csv")
    p.add_argument("--label-col", default="action_label")
    p.add_argument("--group-col", default="experiment_id")
    p.add_argument("--outdir", default="webhook/models")
    p.add_argument("--reportdir", default="ml/reports")
    p.add_argument("--threshold", type=float, default=0.90)
    p.add_argument("--test_size", type=float, default=0.5)  # with 2 experiments, 50/50 is sensible
    p.add_argument("--random_state", type=int, default=42)
    return p.parse_args()


def normalize_label(y: pd.Series) -> pd.Series:
    """
    Supports labels as strings ('auto_scale'/'no_action') or ints (1/0).
    """
    if y.dtype == object:
        y2 = y.astype(str).str.strip().str.lower()
        mapping = {"auto_scale": 1, "no_action": 0, "1": 1, "0": 0}
        return y2.map(mapping)
    return y.astype(int)


def main() -> None:
    args = parse_args()

    df = pd.read_csv(args.dataset)

    # Required columns
    for c in FEATURES + [args.label_col]:
        if c not in df.columns:
            raise ValueError(f"Missing required column: {c}")

    # Feature matrix + label
    X = df[FEATURES].copy()
    y = normalize_label(df[args.label_col])

    if y.isna().any():
        bad = df.loc[y.isna(), args.label_col].value_counts().head(10).to_dict()
        raise ValueError(f"Unrecognized label values: {bad}")

    if X.isna().any().any():
        raise ValueError(f"Missing feature values:\n{X.isna().sum()}")

    # Group split (prevents leakage across experiments)
    split_info = {}
    if args.group_col in df.columns and df[args.group_col].nunique() >= 2:
        groups = df[args.group_col].astype(str)
        gss = GroupShuffleSplit(n_splits=1, test_size=args.test_size, random_state=args.random_state)
        train_idx, test_idx = next(gss.split(X, y, groups=groups))
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        split_info = {
            "type": "GroupShuffleSplit",
            "group_col": args.group_col,
            "train_groups": sorted(groups.iloc[train_idx].unique().tolist()),
            "test_groups": sorted(groups.iloc[test_idx].unique().tolist()),
        }
    else:
        raise ValueError("experiment_id (group_col) missing or has <2 unique values; cannot do group split.")

    # Pipeline model
    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]
    )

    model.fit(X_train, y_train)

    # Thresholded predictions
    proba = model.predict_proba(X_test)[:, 1]
    y_pred_thr = (proba >= args.threshold).astype(int)

    cm = confusion_matrix(y_test, y_pred_thr)
    report_txt = classification_report(y_test, y_pred_thr, digits=4)

    pr, rc, f1, _ = precision_recall_fscore_support(y_test, y_pred_thr, average="binary", zero_division=0)

    # Output dirs
    outdir = Path(args.outdir)
    reportdir = Path(args.reportdir)
    outdir.mkdir(parents=True, exist_ok=True)
    reportdir.mkdir(parents=True, exist_ok=True)

    # Save model + meta
    model_path = outdir / "autoscale_classifier.joblib"
    joblib.dump(model, model_path)

    meta = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": str(Path(args.dataset).as_posix()),
        "features": FEATURES,
        "label_col": args.label_col,
        "label_positive": "auto_scale",
        "threshold": args.threshold,
        "split": split_info,
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "metrics_at_threshold": {
            "precision": float(pr),
            "recall": float(rc),
            "f1": float(f1),
            "confusion_matrix": cm.tolist(),
        },
        "notes": "Baseline StandardScaler + LogisticRegression for autoscale vs no_action.",
    }

    meta_path = outdir / "autoscale_classifier_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))

    # Save report files
    (reportdir / "autoscale_classifier_report.txt").write_text(str(report_txt))
    (reportdir / "autoscale_confusion_matrix.json").write_text(
        json.dumps({"threshold": args.threshold, "confusion_matrix": cm.tolist()}, indent=2)
    )

    print("Saved model :", model_path)
    print("Saved meta  :", meta_path)
    print("Saved report:", reportdir / "autoscale_classifier_report.txt")
    print("\n--- classification_report (threshold {:.2f}) ---\n{}".format(args.threshold, report_txt))
    print("confusion_matrix:", cm.tolist())


if __name__ == "__main__":
    main()
