"""
Task 1 - Exploratory Data Analysis & Preprocessing Pipeline
============================================================
Loads ev_campus_dataset.csv, cleans it, engineers features, prints EDA and
group-by summaries, and saves cleaned_ev_dataset.csv.

Run:  python data_pipeline.py
      python data_pipeline.py --input ev_campus_dataset.csv --output-dir .
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NUMERIC_COLS = ["Start_Hour", "Duration_Mins", "Energy_kWh",
                "Overstay_Mins", "Battery_Temp_C"]
CATEGORICAL_COLS = ["Charger_Type", "User_Type"]
TARGET = "Grid_Status_Label"
VALID_LABELS = {"Normal", "Overheated", "Grid_Surge"}

# Peak tariff window 12:00-17:00. Start_Hour is an integer hour, and the data
# shows Grid_Surge sessions starting at hour 17, so hours 12..17 are inclusive.
PEAK_START, PEAK_END = 12, 17

# Physically valid ranges; values outside are treated as sensor/entry errors.
VALID_RANGES = {
    "Start_Hour": (0, 23),
    "Duration_Mins": (1, 24 * 60),
    "Energy_kWh": (0.1, 200),
    "Overstay_Mins": (0, 24 * 60),
    "Battery_Temp_C": (-20, 80),
}


def section(title):
    """Print a readable section header in the console output."""
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ---------------------------------------------------------------------------
# Step 1: Load and explore
# ---------------------------------------------------------------------------
def load_data(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    required = {"Session_ID", TARGET, *NUMERIC_COLS, *CATEGORICAL_COLS}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("The dataset is empty.")
    return df


def explore(df):
    section("STEP 1 - EXPLORATORY DATA ANALYSIS")
    print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns\n")
    df.info()
    print("\nDescriptive statistics (numeric):")
    print(df.describe().round(2).to_string())
    print("\nMissing values per column:")
    print(df.isna().sum().to_string())
    print("\nTarget distribution:")
    counts = df[TARGET].value_counts()
    print(pd.DataFrame({"count": counts,
                        "percent": (counts / len(df) * 100).round(1)}).to_string())


# ---------------------------------------------------------------------------
# Step 2: Clean and sanitise
# ---------------------------------------------------------------------------
def clean(df, report):
    section("STEP 2 - DATA CLEANING & SANITISATION")
    df = df.copy()
    report["rows_before"] = len(df)
    report["missing_before"] = {k: int(v) for k, v in df.isna().sum().items()}

    # 2a. Tidy text: strip spaces, turn blank strings into real missing values.
    for col in ["Session_ID", TARGET, *CATEGORICAL_COLS]:
        df[col] = df[col].astype("string").str.strip().replace("", pd.NA)

    # 2b. Rows without an ID or a valid target cannot be used -> drop them.
    bad_rows = df["Session_ID"].isna() | ~df[TARGET].isin(VALID_LABELS)
    report["rows_dropped_no_id_or_invalid_label"] = int(bad_rows.sum())
    df = df[~bad_rows]

    # 2c. Remove duplicates: exact copies first, then repeated Session_IDs.
    exact = int(df.duplicated().sum())
    df = df.drop_duplicates()
    repeated_id = int(df.duplicated("Session_ID").sum())
    df = df.drop_duplicates("Session_ID", keep="first")
    report["duplicates_removed"] = {"exact_rows": exact, "repeated_session_id": repeated_id}
    print(f"Duplicates removed: {exact} exact rows, {repeated_id} repeated Session_IDs")

    # 2d. Coerce numeric columns; out-of-range values become NaN (then imputed).
    report["invalid_values_set_to_nan"] = {}
    for col in NUMERIC_COLS:
        values = pd.to_numeric(df[col], errors="coerce")
        low, high = VALID_RANGES[col]
        invalid = values.notna() & ~values.between(low, high)
        report["invalid_values_set_to_nan"][col] = int(invalid.sum())
        df[col] = values.mask(invalid)

    # 2e. Median imputation for numeric columns (robust to skew/outliers).
    report["median_imputation"] = {}
    for col in NUMERIC_COLS:
        n_missing = int(df[col].isna().sum())
        median = float(df[col].median())
        df[col] = df[col].fillna(median)
        report["median_imputation"][col] = {"median": median, "values_filled": n_missing}
        if n_missing:
            print(f"Imputed {n_missing:>3} missing {col:<15} with median = {median}")

    # 2f. Mode imputation for categorical predictors (none missing in this data).
    for col in CATEGORICAL_COLS:
        if df[col].isna().any():
            df[col] = df[col].fillna(df[col].mode().iloc[0])

    # Integer columns stay integers after imputation.
    df["Start_Hour"] = df["Start_Hour"].round().astype(int)
    df["Overstay_Mins"] = df["Overstay_Mins"].round().astype(int)

    report["rows_after"] = len(df)
    print(f"Rows: {report['rows_before']} -> {report['rows_after']}; "
          f"missing values left: {int(df.isna().sum().sum())}")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Step 3: Feature engineering
# ---------------------------------------------------------------------------
def engineer_features(df, report):
    section("STEP 3 - FEATURE ENGINEERING")
    df = df.copy()

    # 3a. Peak flag: dataset has Start_Hour but no Peak_Hour_Flag column.
    df["Peak_Hour_Flag"] = df["Start_Hour"].between(PEAK_START, PEAK_END).astype(int)

    # 3b. Charging power rate (kW) = energy / hours, rounded for readability.
    hours = df["Duration_Mins"] / 60
    df["Power_kW"] = np.round(df["Energy_kWh"] / hours, 3)

    # 3c. Efficiency group: AC and DC have very different power scales, so the
    #     tertiles (33rd / 67th percentile) are computed within each charger.
    df["Energy_Efficiency_Group"] = (
        df.groupby("Charger_Type")["Power_kW"]
          .transform(lambda s: pd.qcut(s, 3, labels=["Low", "Medium", "High"]).astype(str))
    )
    thresholds = (df.groupby("Charger_Type")["Power_kW"]
                    .quantile([1 / 3, 2 / 3]).unstack().round(3))
    thresholds.columns = ["Low_Medium_cut_kW", "Medium_High_cut_kW"]
    print("Power_kW tertile cut-offs by charger type:")
    print(thresholds.to_string())
    print("\nEfficiency group counts:")
    print(pd.crosstab(df["Charger_Type"], df["Energy_Efficiency_Group"]).to_string())

    report["peak_rule"] = f"Peak_Hour_Flag = 1 if {PEAK_START} <= Start_Hour <= {PEAK_END}"
    report["efficiency_rule"] = ("Power_kW tertiles within each Charger_Type "
                                 "(relative charging-rate proxy).")
    report["efficiency_thresholds_kW"] = thresholds.reset_index().to_dict("records")
    return df


# ---------------------------------------------------------------------------
# Step 4: Statistical aggregation
# ---------------------------------------------------------------------------
def summarise(df):
    section("STEP 4 - GROUP-BY SUMMARY TABLES")
    # The CSV has no Ambient_Temp_C column, so Battery_Temp_C is the
    # temperature measure compared here (clearly labelled as battery temp).
    aggregations = dict(
        Sessions=("Session_ID", "count"),
        Avg_Energy_kWh=("Energy_kWh", "mean"),
        Total_Energy_kWh=("Energy_kWh", "sum"),
        Avg_Battery_Temp_C=("Battery_Temp_C", "mean"),
        Avg_Duration_Mins=("Duration_Mins", "mean"),
        Avg_Power_kW=("Power_kW", "mean"),
    )
    tables = {
        "summary_by_charger": df.groupby("Charger_Type").agg(**aggregations),
        "summary_by_peak": df.groupby("Peak_Hour_Flag").agg(**aggregations),
        "summary_by_charger_and_peak": df.groupby(["Charger_Type", "Peak_Hour_Flag"]).agg(**aggregations),
    }
    # Extra insight: status share (%) per charger type and peak period.
    tables["status_rate_by_charger_and_peak"] = (
        pd.crosstab([df["Charger_Type"], df["Peak_Hour_Flag"]], df[TARGET],
                    normalize="index").mul(100))
    for name, table in tables.items():
        tables[name] = table.round(2).reset_index()
        print(f"\n{name}:\n{tables[name].to_string(index=False)}")
    return tables


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="EV campus data pipeline (Task 1)")
    parser.add_argument("--input", type=Path, default=Path("ev_campus_dataset.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    report = {"source_file": args.input.name}
    raw = load_data(args.input)
    explore(raw)
    cleaned = clean(raw, report)
    cleaned = engineer_features(cleaned, report)
    tables = summarise(cleaned)

    # Final quality gates: pipeline stops if the output is not sanitised.
    assert cleaned.isna().sum().sum() == 0, "Cleaned data still has missing values"
    assert not cleaned["Session_ID"].duplicated().any(), "Duplicate Session_IDs remain"

    section("STEP 5 - OUTPUT GENERATION")
    cleaned.to_csv(args.output_dir / "cleaned_ev_dataset.csv", index=False)
    for name, table in tables.items():
        table.to_csv(args.output_dir / f"{name}.csv", index=False)
    report["missing_after"] = int(cleaned.isna().sum().sum())
    report["columns_out"] = cleaned.columns.tolist()
    report["data_notes"] = [
        "Charger_Type values in the CSV are 'AC'/'DC' (brief: AC_Fast/DC_Ultra); kept as-is.",
        "No Ambient_Temp_C column in the CSV; Battery_Temp_C used and labelled as such.",
        "No Peak_Hour_Flag column in the CSV; derived from Start_Hour (12-17 inclusive).",
    ]
    (args.output_dir / "cleaning_report.json").write_text(json.dumps(report, indent=2))
    print(f"Saved cleaned_ev_dataset.csv ({len(cleaned)} rows, {cleaned.shape[1]} columns), "
          f"{len(tables)} summary tables and cleaning_report.json")


if __name__ == "__main__":
    main()
