#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


FEATURES = ["rps", "p95", "http_5xx_rate", "cpu_sat"]
ALIASES = {
    "p95": ["p95_latency_s", "latency", "latency_p95"],
    "http_5xx_rate": ["error_rate", "http5xx_rate", "errors"],
    "cpu_sat": ["cpu_usage", "cpu"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CSV containing restart experiment feature windows.")
    parser.add_argument("--output", default="experiments/dataset_restart.csv")
    parser.add_argument("--experiment-id", default=None)
    parser.add_argument("--error-threshold", type=float, default=0.20)
    parser.add_argument("--cpu-upper", type=float, default=0.70)
    parser.add_argument("--p95-threshold", type=float, default=0.50)
    parser.add_argument(
        "--drop-phase-start-seconds",
        type=float,
        default=0.0,
        help=(
            "Drop rows from the start of each experiment/phase group before labeling. "
            "Use this to remove Prometheus range-vector carryover after phase switches."
        ),
    )
    parser.add_argument(
        "--trimmed-output",
        default=None,
        help="Optional CSV path for feature windows after phase-start trimming.",
    )
    return parser.parse_args()


def label_restart(row: pd.Series, error_threshold: float, cpu_upper: float, p95_threshold: float) -> str:
    error_rate = float(row["http_5xx_rate"])
    cpu_sat = float(row["cpu_sat"])
    p95 = float(row["p95"])
    if error_rate >= error_threshold and cpu_sat < cpu_upper and p95 > p95_threshold:
        return "auto_restart"
    return "no_action"


def drop_phase_starts(df: pd.DataFrame, seconds: float) -> pd.DataFrame:
    if seconds <= 0:
        return df.copy()
    if "phase" not in df.columns:
        raise ValueError("--drop-phase-start-seconds requires a phase column in the input CSV.")

    group_columns = ["experiment_id", "phase"]
    phase_start = df.groupby(group_columns)["window_end"].transform("min")
    keep = df["window_end"] >= phase_start + seconds
    return df.loc[keep].copy()


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.input)
    for canonical, aliases in ALIASES.items():
        if canonical in df.columns:
            continue
        for alias in aliases:
            if alias in df.columns:
                df[canonical] = df[alias]
                break

    required_columns = [*FEATURES, "window_start", "window_end"]
    missing = [name for name in required_columns if name not in df.columns]
    if missing:
        raise ValueError(f"Missing required restart dataset columns: {missing}")

    dataset = df.copy()
    if "experiment_id" not in dataset.columns:
        dataset["experiment_id"] = args.experiment_id or Path(args.input).stem

    dataset = drop_phase_starts(dataset, args.drop_phase_start_seconds)

    if args.trimmed_output:
        trimmed_output = Path(args.trimmed_output)
        trimmed_output.parent.mkdir(parents=True, exist_ok=True)
        dataset.to_csv(trimmed_output, index=False)
        print(f"Saved trimmed restart feature windows: {trimmed_output}")
        print(f"Trimmed rows: {len(dataset)}")

    dataset["label"] = dataset.apply(
        lambda row: label_restart(row, args.error_threshold, args.cpu_upper, args.p95_threshold),
        axis=1,
    )
    class_counts = dataset["label"].value_counts().to_dict()
    if len(class_counts) < 2:
        raise ValueError(
            "Restart dataset contains only one class after labeling. "
            f"class_distribution={class_counts}. Collect both restart and no_action windows before training."
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    columns = [*FEATURES, "label", "experiment_id", "window_start", "window_end"]
    dataset[columns].to_csv(output, index=False)

    print(f"Saved restart dataset: {output}")
    print(f"Rows: {len(dataset)}")
    print(dataset["label"].value_counts().to_string())


if __name__ == "__main__":
    main()
