from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import GroupShuffleSplit, train_test_split


FEATURES = ["rps", "p95", "http_5xx_rate", "cpu_sat"]
POSITIVE_LABEL = "auto_restart"
NEGATIVE_LABEL = "no_action"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="experiments/dataset_restart.csv")
    parser.add_argument("--label-col", default="action_label")
    parser.add_argument("--group-col", default="experiment_id")
    parser.add_argument("--outdir", default="webhook/models")
    parser.add_argument("--reportdir", default="ml/reports")
    parser.add_argument("--threshold", type=float, default=0.90)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def normalize_label(labels: pd.Series) -> pd.Series:
    values = labels.astype(str).str.strip().str.lower()
    mapping = {
        POSITIVE_LABEL: POSITIVE_LABEL,
        NEGATIVE_LABEL: NEGATIVE_LABEL,
        "1": POSITIVE_LABEL,
        "0": NEGATIVE_LABEL,
        "true": POSITIVE_LABEL,
        "false": NEGATIVE_LABEL,
    }
    return values.map(mapping)


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.dataset)

    missing = [name for name in FEATURES + [args.label_col] if name not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    X = df[FEATURES].copy()
    y = normalize_label(df[args.label_col])
    if y.isna().any():
        bad = df.loc[y.isna(), args.label_col].value_counts(dropna=False).head(10).to_dict()
        raise ValueError(f"Unrecognized labels: {bad}")
    if sorted(y.unique().tolist()) != sorted([NEGATIVE_LABEL, POSITIVE_LABEL]):
        raise ValueError("Restart training requires both no_action and auto_restart labels.")
    if X.isna().any().any():
        raise ValueError(f"Missing feature values:\n{X.isna().sum()}")

    split_info = {"type": "train_test_split", "stratified": True}
    if args.group_col in df.columns and df[args.group_col].nunique() >= 2:
        groups = df[args.group_col].astype(str)
        splitter = GroupShuffleSplit(n_splits=1, test_size=args.test_size, random_state=args.random_state)
        train_idx, test_idx = next(splitter.split(X, y, groups=groups))
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        split_info = {
            "type": "GroupShuffleSplit",
            "group_col": args.group_col,
            "train_groups": sorted(groups.iloc[train_idx].unique().tolist()),
            "test_groups": sorted(groups.iloc[test_idx].unique().tolist()),
        }
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=args.test_size,
            random_state=args.random_state,
            stratify=y,
        )

    model = RandomForestClassifier(
        n_estimators=150,
        max_depth=8,
        class_weight="balanced",
        random_state=args.random_state,
    )
    model.fit(X_train, y_train)

    positive_index = list(model.classes_).index(POSITIVE_LABEL)
    proba = model.predict_proba(X_test)[:, positive_index]
    y_pred = pd.Series(
        [POSITIVE_LABEL if value >= args.threshold else NEGATIVE_LABEL for value in proba],
        index=y_test.index,
    )

    labels = [NEGATIVE_LABEL, POSITIVE_LABEL]
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    report_txt = classification_report(y_test, y_pred, labels=labels, digits=4, zero_division=0)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test,
        y_pred,
        labels=labels,
        average="binary",
        pos_label=POSITIVE_LABEL,
        zero_division=0,
    )

    outdir = Path(args.outdir)
    reportdir = Path(args.reportdir)
    outdir.mkdir(parents=True, exist_ok=True)
    reportdir.mkdir(parents=True, exist_ok=True)

    model_path = outdir / "restart_classifier.joblib"
    joblib.dump(model, model_path)
    meta_path = outdir / "restart_classifier_meta.json"
    class_distribution = y.value_counts().to_dict()
    training_date = datetime.now(timezone.utc).isoformat()

    meta = {
        "training_date": training_date,
        "created_at_utc": training_date,
        "dataset": str(Path(args.dataset).as_posix()),
        "feature_order": FEATURES,
        "features": FEATURES,
        "label_col": args.label_col,
        "label_positive": POSITIVE_LABEL,
        "class_labels": list(model.classes_),
        "label_classes": list(model.classes_),
        "class_distribution": {str(label): int(count) for label, count in class_distribution.items()},
        "threshold": args.threshold,
        "model_path": str(model_path.as_posix()),
        "metadata_path": str(meta_path.as_posix()),
        "split": split_info,
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "model": {
            "type": "RandomForestClassifier",
            "n_estimators": 150,
            "max_depth": 8,
            "class_weight": "balanced",
            "random_state": args.random_state,
        },
        "metrics_at_threshold": {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "confusion_matrix_labels": labels,
            "confusion_matrix": cm.tolist(),
        },
        "notes": "Binary restart classifier using the same four-feature vector as autoscale.",
    }

    meta_path.write_text(json.dumps(meta, indent=2))

    (reportdir / "restart_classifier_report.txt").write_text(report_txt)
    (reportdir / "restart_classifier_confusion_matrix.json").write_text(
        json.dumps({"threshold": args.threshold, "labels": labels, "confusion_matrix": cm.tolist()}, indent=2)
    )

    print("Saved model :", model_path)
    print("Saved meta  :", meta_path)
    print("Saved report:", reportdir / "restart_classifier_report.txt")
    print(f"\n--- classification_report (threshold {args.threshold:.2f}) ---\n{report_txt}")
    print("confusion_matrix:", cm.tolist())


if __name__ == "__main__":
    main()
