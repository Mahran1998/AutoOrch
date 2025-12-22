#!/usr/bin/env python3
import os
import glob
import pandas as pd


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPERIMENTS_DIR = os.path.join(BASE_DIR, "experiments")

CPU_LIMIT_CORES = 0.3           # demo-backend CPU limit (300m)
CPU_SAT_THRESHOLD = 0.7         # >70% of limit → auto_scale


def find_latest_experiment(prefix: str) -> str:
    """
    Find the latest experiment directory under ./experiments
    whose name starts with the given prefix (e.g. 'exp0_v2', 'exp1_autoscale').
    """
    pattern = os.path.join(EXPERIMENTS_DIR, f"{prefix}_*")
    candidates = sorted(glob.glob(pattern))
    if not candidates:
        raise RuntimeError(f"No experiment directories found for prefix '{prefix}' under {EXPERIMENTS_DIR}")
    return candidates[-1]  # lexicographically last → latest timestamp


def load_experiment(exp_dir: str, experiment_id: str, has_cpu_sat_csv: bool) -> pd.DataFrame:
    """
    Load a single experiment's CSVs, merge them on timestamp, and compute cpu_saturation.
    Returns a DataFrame with columns:
      timestamp, rps, p95, http_5xx_rate, cpu, cpu_sat, cpu_pct, experiment_id
    """
    csv_dir = os.path.join(exp_dir, "csv")

    def read_csv(name):
        path = os.path.join(csv_dir, name)
        if not os.path.exists(path):
            return None
        df = pd.read_csv(path)
        if df.empty:
            return None
        return df

    # Load base metrics
    rps_df = read_csv("requests_rate.csv")
    lat_df = read_csv("p95_latency.csv")
    cpu_df = read_csv("container_cpu.csv")
    http5_df = read_csv("http_5xx.csv")
    cpu_sat_df = read_csv("cpu_saturation.csv") if has_cpu_sat_csv else None

    if rps_df is None or lat_df is None or cpu_df is None:
        raise RuntimeError(f"Missing core CSVs in {csv_dir}")

    # Merge on timestamp (inner join → keep rows where we have all metrics)
    df = rps_df.merge(lat_df, on="timestamp", suffixes=("_rps", "_lat"))
    df = df.merge(cpu_df, on="timestamp")

    # Rename
    df = df.rename(columns={
        "value_rps": "rps",
        "value_lat": "p95",
        "value": "cpu"   # from container_cpu.csv
    })

    # Handle http_5xx_rate
    if http5_df is not None:
        df_http = http5_df.rename(columns={"value": "http_5xx_rate"})
        df = df.merge(df_http[["timestamp", "http_5xx_rate"]], on="timestamp", how="left")
    else:
        df["http_5xx_rate"] = 0.0

    # Compute or use cpu_saturation
    if cpu_sat_df is not None:
        df_sat = cpu_sat_df.rename(columns={"value": "cpu_sat"})
        df = df.merge(df_sat[["timestamp", "cpu_sat"]], on="timestamp", how="left")
    else:
        df["cpu_sat"] = df["cpu"] / CPU_LIMIT_CORES

    # If any NaNs remain (e.g., missing http_5xx_rate), fill with 0
    df["http_5xx_rate"] = df["http_5xx_rate"].fillna(0.0)
    df["cpu_sat"] = df["cpu_sat"].fillna(df["cpu"] / CPU_LIMIT_CORES)

    # Add cpu percentage of limit
    df["cpu_pct"] = df["cpu_sat"] * 100.0

    # Add experiment id
    df["experiment_id"] = experiment_id

    # Keep only the columns we care about
    df = df[["timestamp", "rps", "p95", "http_5xx_rate", "cpu", "cpu_sat", "cpu_pct", "experiment_id"]]

    return df


def add_action_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 'action_label' column based on cpu_saturation threshold.
    """
    df = df.copy()
    df["action_label"] = df["cpu_sat"].apply(
        lambda x: "auto_scale" if x > CPU_SAT_THRESHOLD else "no_action"
    )
    return df


def main():
    # 1) Locate latest Exp0 v2 and Exp1 directories
    exp0_dir = find_latest_experiment("exp0_v2_calibration_limits")
    exp1_dir = find_latest_experiment("exp1_autoscale")

    print(f"Using Exp0 v2 dir: {exp0_dir}")
    print(f"Using Exp1 dir:    {exp1_dir}")

    # 2) Load experiments
    exp0_df = load_experiment(exp0_dir, experiment_id="exp0_v2", has_cpu_sat_csv=False)
    exp1_df = load_experiment(exp1_dir, experiment_id="exp1_autoscale", has_cpu_sat_csv=True)

    # 3) Concatenate
    combined = pd.concat([exp0_df, exp1_df], ignore_index=True)

    # 4) Add action label
    combined = add_action_label(combined)

    # 5) Sort by timestamp (optional, just for readability)
    combined = combined.sort_values(by=["timestamp", "experiment_id"]).reset_index(drop=True)

    # 6) Save
    out_path = os.path.join(EXPERIMENTS_DIR, "dataset_autoscale.csv")
    combined.to_csv(out_path, index=False)
    print(f"[+] Saved dataset to: {out_path}")
    print(f"[i] Total rows: {len(combined)}")
    print(f"[i] Label counts:\n{combined['action_label'].value_counts()}")


if __name__ == "__main__":
    main()

