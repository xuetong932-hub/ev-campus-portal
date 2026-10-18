"""
Task 2 - Machine Learning Workflow & Model Evaluation
=====================================================
Predicts Grid_Status_Label ('Normal', 'Overheated', 'Grid_Surge') with the
7-step ML framework and saves the best model as ev_model.pkl.

Run:  python train_ev_model.py
Outputs: ev_model.pkl, model_metadata.json, test_predictions.csv and
         figures/tables in the reports/ folder.
"""

import argparse
import json
import platform
from importlib.metadata import version
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")                      # render plots without a screen
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, precision_recall_fscore_support)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

TARGET = "Grid_Status_Label"
LABELS = ["Normal", "Overheated", "Grid_Surge"]
CATEGORICAL = ["Charger_Type", "User_Type"]
NUMERIC = ["Start_Hour", "Peak_Hour_Flag", "Duration_Mins", "Energy_kWh",
           "Overstay_Mins", "Battery_Temp_C"]
FEATURES = CATEGORICAL + NUMERIC
PEAK_START, PEAK_END = 12, 17              # same rule as Task 1
SEED = 42


def add_peak_flag(frame):
    """Deterministic rule from Task 1 (uses no statistics, so no leakage)."""
    frame = frame.copy()
    hour = pd.to_numeric(frame["Start_Hour"], errors="coerce")
    frame["Peak_Hour_Flag"] = hour.between(PEAK_START, PEAK_END).astype(float).where(hour.notna())
    return frame


def build_pipeline(classifier, scale=False):
    """Preprocessing lives INSIDE the pipeline, so medians / one-hot categories
    are learned from training folds only and are re-used at inference time."""
    numeric_steps = [("impute", SimpleImputer(strategy="median"))]
    if scale:                              # KNN is distance-based -> needs scaling
        numeric_steps.append(("scale", StandardScaler()))
    preprocess = ColumnTransformer([
        ("numeric", Pipeline(numeric_steps), NUMERIC),
        ("categorical", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]), CATEGORICAL),
    ])
    return Pipeline([("preprocess", preprocess), ("classifier", classifier)])


def metric_row(name, y_true, y_pred):
    row = {"model": name, "accuracy": accuracy_score(y_true, y_pred)}
    for avg in ["macro", "weighted"]:
        p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, labels=LABELS,
                                                     average=avg, zero_division=0)
        row.update({f"precision_{avg}": p, f"recall_{avg}": r, f"f1_{avg}": f})
    return row


def plot_confusion(ax, y_true, y_pred, title):
    cm = confusion_matrix(y_true, y_pred, labels=LABELS)
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False,
                xticklabels=LABELS, yticklabels=LABELS, ax=ax)
    ax.set(title=title, xlabel="Predicted label", ylabel="True label")
    ax.tick_params(axis="y", rotation=0)
    return cm


def main():
    parser = argparse.ArgumentParser(description="Train EV grid-status classifier (Task 2)")
    parser.add_argument("--input", type=Path, default=Path("ev_campus_dataset.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    args = parser.parse_args()
    out = args.output_dir
    reports = out / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # STEP 1 - Define the problem
    # ------------------------------------------------------------------
    # 3-class classification. Classes are imbalanced (Normal ~75%), so models
    # are selected by MACRO F1, which weights every class equally.

    # ------------------------------------------------------------------
    # STEP 2 - Collect the data
    # ------------------------------------------------------------------
    # The RAW file is used (not the Task 1 output) so that median imputation
    # is learned from training rows only -> no information leaks from the test set.
    df = pd.read_csv(args.input)
    df = df.drop_duplicates("Session_ID").dropna(subset=[TARGET])
    df = add_peak_flag(df)
    print(f"Loaded {len(df)} sessions\nClass counts:\n{df[TARGET].value_counts().to_string()}")

    # ------------------------------------------------------------------
    # STEP 3 - Prepare data: feature selection + 80/20 stratified split
    # ------------------------------------------------------------------
    # Session_ID is an identifier (no signal) and is excluded.
    X, y = df[FEATURES], df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=SEED)
    print(f"Train: {len(X_train)} rows | Test: {len(X_test)} rows")

    # ------------------------------------------------------------------
    # STEP 4 - Choose candidate models (3 different families + baseline)
    # ------------------------------------------------------------------
    candidates = {
        "DecisionTree": (build_pipeline(DecisionTreeClassifier(random_state=SEED)), {
            "classifier__max_depth": [3, 4, 6, None],
            "classifier__min_samples_leaf": [1, 5],
            "classifier__class_weight": [None, "balanced"]}),
        "RandomForest": (build_pipeline(RandomForestClassifier(n_estimators=300, random_state=SEED)), {
            "classifier__max_depth": [4, 8, None],
            "classifier__min_samples_leaf": [1, 5],
            "classifier__class_weight": [None, "balanced"]}),
        "KNN": (build_pipeline(KNeighborsClassifier(), scale=True), {
            "classifier__n_neighbors": [3, 5, 9, 15],
            "classifier__weights": ["uniform", "distance"]}),
    }

    # ------------------------------------------------------------------
    # STEP 5 - Train & tune with 5-fold stratified cross-validation
    # ------------------------------------------------------------------
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    searches = {}
    for name, (pipe, grid) in candidates.items():
        search = GridSearchCV(pipe, grid, scoring="f1_macro", cv=cv, n_jobs=-1)
        search.fit(X_train, y_train)
        searches[name] = search
        print(f"{name:<13} CV macro-F1 = {search.best_score_:.4f}  best = {search.best_params_}")

    # The winner is chosen on CV score BEFORE looking at the test set.
    best_name = max(searches, key=lambda n: searches[n].best_score_)
    best_model = searches[best_name].best_estimator_

    # ------------------------------------------------------------------
    # STEP 6 - Evaluate on the untouched 20% test set
    # ------------------------------------------------------------------
    rows, preds = [], {}
    for name, search in searches.items():
        preds[name] = search.predict(X_test)
        row = metric_row(name, y_test, preds[name])
        row.update(cv_f1_macro=search.best_score_,
                   cv_f1_std=search.cv_results_["std_test_score"][search.best_index_],
                   best_params=str(search.best_params_), selected=name == best_name)
        rows.append(row)
        report = classification_report(y_test, preds[name], labels=LABELS,
                                       output_dict=True, zero_division=0)
        pd.DataFrame(report).T.round(4).to_csv(reports / f"classification_report_{name}.csv")
        print(f"\n--- {name} (test set) ---")
        print(classification_report(y_test, preds[name], labels=LABELS, zero_division=0, digits=3))

    # Baseline: always predict the majority class. Any useful model must beat it.
    dummy = DummyClassifier(strategy="most_frequent").fit(X_train, y_train)
    baseline = metric_row("Baseline_MostFrequent", y_test, dummy.predict(X_test))
    rows.append({**baseline, "selected": False})

    # Overfitting check: train vs test accuracy of every model.
    for row in rows:
        if row["model"] in searches:
            row["train_accuracy"] = accuracy_score(y_train, searches[row["model"]].predict(X_train))
    comparison = pd.DataFrame(rows)
    comparison.round(4).to_csv(reports / "model_comparison.csv", index=False)
    print("\nModel comparison (test set):")
    print(comparison[["model", "cv_f1_macro", "train_accuracy", "accuracy", "f1_macro",
                      "selected"]].round(4).to_string(index=False))

    # Seaborn confusion matrices - one combined figure + one per model.
    fig, axes = plt.subplots(1, len(searches), figsize=(6 * len(searches), 5), layout="constrained")
    matrices = {}
    for ax, name in zip(axes, searches):
        matrices[name] = plot_confusion(ax, y_test, preds[name],
                                        f"{name}\naccuracy {accuracy_score(y_test, preds[name]):.1%}")
    fig.suptitle("Confusion matrices - held-out test set (n=%d)" % len(y_test), fontweight="bold")
    fig.savefig(reports / "confusion_matrices_all.png", dpi=160)
    plt.close(fig)
    for name in searches:
        fig, ax = plt.subplots(figsize=(6.5, 5), layout="constrained")
        plot_confusion(ax, y_test, preds[name], f"{name} - test set confusion matrix")
        fig.savefig(reports / f"confusion_matrix_{name}.png", dpi=160)
        plt.close(fig)

    # Model comparison bar chart.
    plot_df = comparison.melt(id_vars="model", value_vars=["accuracy", "precision_macro",
                                                           "recall_macro", "f1_macro"])
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    sns.barplot(data=plot_df, x="model", y="value", hue="variable", ax=ax)
    ax.set(title="Model comparison on the test set", ylabel="Score", xlabel="", ylim=(0, 1.05))
    ax.legend(title="", ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.08))
    fig.savefig(reports / "model_comparison.png", dpi=160)
    plt.close(fig)

    # Feature importance (permutation, on the test set, for the selected model).
    perm = permutation_importance(best_model, X_test, y_test, scoring="f1_macro",
                                  n_repeats=20, random_state=SEED)
    importance = (pd.DataFrame({"feature": FEATURES, "importance": perm.importances_mean,
                                "std": perm.importances_std})
                    .sort_values("importance", ascending=False))
    importance.round(4).to_csv(reports / "feature_importance.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    sns.barplot(data=importance, x="importance", y="feature", color="#2a7f8f", ax=ax)
    ax.set(title=f"Permutation importance - {best_name}", xlabel="Drop in macro F1 when shuffled", ylabel="")
    fig.savefig(reports / "feature_importance.png", dpi=160)
    plt.close(fig)
    print(f"\nFeature importance ({best_name}):\n{importance.round(4).to_string(index=False)}")

    # Explainability: print the learned rules if the winner is a decision tree.
    if best_name == "DecisionTree":
        from sklearn.tree import export_text, plot_tree
        names = list(best_model.named_steps["preprocess"].get_feature_names_out())
        names = [n.split("__", 1)[1] for n in names]
        tree = best_model.named_steps["classifier"]
        rules = export_text(tree, feature_names=names, decimals=1)
        (reports / "decision_tree_rules.txt").write_text(rules)
        print(f"\nLearned decision rules:\n{rules}")
        fig, ax = plt.subplots(figsize=(14, 6), layout="constrained")
        plot_tree(tree, feature_names=names, class_names=list(tree.classes_), filled=True,
                  rounded=True, impurity=False, proportion=True, fontsize=9, ax=ax)
        fig.savefig(reports / "decision_tree.png", dpi=160)
        plt.close(fig)

    # Error analysis: what is the best ANY model could do on this data?
    # Overheated <=> Battery_Temp_C > 43; Grid_Surge only starts in hours 12-17.
    # Inside that window (temp <= 43) Surge and Normal look identical, so some
    # errors are unavoidable (irreducible noise).
    full = add_peak_flag(df)
    window = full[(full.Peak_Hour_Flag == 1) & (full.Battery_Temp_C <= 43)]
    ceiling = {
        "overheated_rule_matches": float(((full.Battery_Temp_C > 43) == (full[TARGET] == "Overheated")).mean()),
        "grid_surge_outside_peak": int(((full.Peak_Hour_Flag == 0) & (full[TARGET] == "Grid_Surge")).sum()),
        "peak_window_normal_vs_surge": window[TARGET].value_counts().to_dict(),
        "max_accuracy_possible": float(1 - window[TARGET].value_counts().min() / len(full)),
        "surge_precision_if_all_peak_flagged": float((window[TARGET] == "Grid_Surge").mean()),
    }
    print("\nCeiling analysis:", json.dumps(ceiling, indent=2))

    # ------------------------------------------------------------------
    # STEP 7 - Save (persist) the best model and verify it reloads
    # ------------------------------------------------------------------
    joblib.dump(best_model, out / "ev_model.pkl", compress=3)
    reloaded = joblib.load(out / "ev_model.pkl")
    assert (reloaded.predict(X_test) == preds[best_name]).all(), "Reloaded model differs!"

    test_out = df.loc[X_test.index, ["Session_ID", TARGET]].copy()
    for name in searches:
        test_out[f"predicted_{name}"] = preds[name]
    test_out.to_csv(out / "test_predictions.csv", index=False)

    best_row = comparison.set_index("model").loc[best_name]
    metadata = {
        "selected_model": best_name,
        "selection_rule": "highest 5-fold CV macro F1 on training data (test set not used)",
        "features": FEATURES, "numeric_features": NUMERIC, "categorical_features": CATEGORICAL,
        "labels": LABELS, "peak_rule": f"{PEAK_START} <= Start_Hour <= {PEAK_END}",
        "train_rows": len(X_train), "test_rows": len(X_test),
        # NaN (baseline has no CV score) -> None, so the file is valid JSON.
        "test_metrics": (comparison.drop(columns=["best_params"]).round(4)
                         .astype(object).where(comparison.notna().drop(columns=["best_params"]), None)
                         .to_dict("records")),
        "best_test_accuracy": round(float(best_row["accuracy"]), 4),
        "best_test_f1_macro": round(float(best_row["f1_macro"]), 4),
        "confusion_matrix": {"labels": LABELS, "matrix": matrices[best_name].tolist()},
        "feature_importance": importance.round(4).to_dict("records"),
        "ceiling_analysis": ceiling,
        "python_version": platform.python_version(),
        "package_versions": {p: version(p) for p in
                             ["numpy", "pandas", "scikit-learn", "joblib", "matplotlib", "seaborn"]},
    }
    (out / "model_metadata.json").write_text(json.dumps(metadata, indent=2, default=str))
    print(f"\nSaved {best_name} -> {out / 'ev_model.pkl'} (reload check passed)")


if __name__ == "__main__":
    main()
