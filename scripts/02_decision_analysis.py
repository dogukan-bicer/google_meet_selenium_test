#!/usr/bin/env python3
"""Explore metric decisions against MOS-derived quality labels.

This analysis uses saved metric scores; it does not inject or label software
faults. A low-MOS label is a perceptual-quality proxy only.
"""

import argparse
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "dataset" / "nits_iqa" / "results"
SAVED_SCORES = RESULTS / "results_dinov2.csv"
RECALCULATED_SCORES = RESULTS / "full_nits_iqa_scores.csv"
MOS_FILE = RESULTS / "Score_mos.xlsx"
OUTPUT_ROC = RESULTS / "decision_analysis_roc.csv"
OUTPUT_SUMMARY = RESULTS / "decision_analysis_summary.csv"
OUTPUT_COMBINED = RESULTS / "decision_analysis_tc11.csv"

METRIC_ALIASES = {
    "DINOv2-Base": ["DINOv2-Base (%)", "DINOv2-Base"],
    "DINOv2-Large": ["DINOv2-Large (%)", "DINOv2-Large"],
    "DISTS": ["Dists (%)", "DISTS (%)", "DISTS", "Dists"],
    "SSIM": ["SSIM (%)", "SSIM"],
    "OpenCLIP": ["OpenCLIP (%)", "OpenCLIP"],
}


def read_scores():
    if SAVED_SCORES.is_file():
        path, sep = SAVED_SCORES, ";"
    elif RECALCULATED_SCORES.is_file():
        path, sep = RECALCULATED_SCORES, ","
    else:
        raise FileNotFoundError(
            "Metric scores were not found. Include results_dinov2.csv or run "
            "scripts/01_full_nits_iqa.py on the available image pairs first."
        )

    scores = pd.read_csv(path, sep=sep)
    scores.columns = [str(c).strip() for c in scores.columns]
    if "Ref" not in scores or "Karşıt" not in scores:
        if "ref" in scores and "que" in scores:
            scores = scores.rename(columns={"ref": "Ref", "que": "Karşıt"})
        else:
            raise ValueError(f"Expected reference and distorted-image columns in {path.name}.")
    print(f"Loaded {len(scores)} saved score rows from {path.relative_to(ROOT)}")
    return scores


def read_mos():
    if not MOS_FILE.is_file():
        raise FileNotFoundError(f"MOS workbook not found: {MOS_FILE}")
    mos = pd.read_excel(MOS_FILE)
    if len(mos.columns) < 3:
        raise ValueError("MOS workbook must contain reference, distorted-image, and score columns.")
    # The supplied workbook uses these three columns; positional fallback keeps
    # compatible workbook revisions usable without guessing values.
    if {"Original Image Name", "Distorted Image Name", "Score"}.issubset(mos.columns):
        mos = mos.rename(columns={
            "Original Image Name": "Ref",
            "Distorted Image Name": "Karşıt",
            "Score": "MOS",
        })[["Ref", "Karşıt", "MOS"]]
    else:
        mos = mos.iloc[:, :3].copy()
        mos.columns = ["Ref", "Karşıt", "MOS"]
    mos["Ref"] = mos["Ref"].astype(str).str.strip()
    mos["Karşıt"] = mos["Karşıt"].astype(str).str.strip()
    mos["MOS"] = pd.to_numeric(mos["MOS"], errors="coerce")
    mos = mos.dropna(subset=["MOS"])
    return mos


def prepare_data():
    scores = read_scores()
    mos = read_mos()
    if "MOS" not in scores.columns:
        df = scores.merge(mos, on=["Ref", "Karşıt"], how="left", validate="one_to_one")
    else:
        df = scores.copy()
        df["MOS"] = pd.to_numeric(df["MOS"], errors="coerce")
        if df["MOS"].isna().any():
            df = df.drop(columns="MOS").merge(mos, on=["Ref", "Karşıt"], how="left", validate="one_to_one")

    if df["MOS"].isna().any():
        missing = int(df["MOS"].isna().sum())
        raise ValueError(f"MOS values are missing for {missing} score rows; no synthetic labels were created.")

    rename = {}
    for canonical, aliases in METRIC_ALIASES.items():
        found = next((name for name in aliases if name in df.columns), None)
        if found:
            rename[found] = canonical
    df = df.rename(columns=rename)
    metrics = [name for name in METRIC_ALIASES if name in df.columns]
    if not metrics:
        raise ValueError("No recognized metric columns were found in the score file.")

    # Full recalculation outputs are in [0, 1] for embedding/perceptual scores;
    # the saved comparison CSV uses percentages. Normalize both consistently.
    for metric in metrics:
        values = pd.to_numeric(df[metric], errors="coerce")
        if values.dropna().empty:
            continue
        if values.dropna().max() <= 1.5:
            values = values * 100.0
        df[metric] = values

    df["MOS"] = pd.to_numeric(df["MOS"], errors="coerce")
    df = df.dropna(subset=metrics + ["MOS"]).copy()
    if df.empty:
        raise ValueError("No complete score/MOS rows are available for analysis.")
    print(f"Matched {len(df)} complete rows to MOS; metrics: {', '.join(metrics)}")
    print("Interpretation: MOS-threshold labels represent perceived image quality, not software faults.")
    return df, metrics


def confusion_counts(y_true, y_pred):
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    return tp, tn, fp, fn


def roc_points(y_true, defect_score):
    thresholds = np.r_[np.inf, np.sort(np.unique(defect_score))[::-1]]
    fpr, tpr = [], []
    negatives = max(1, int((y_true == 0).sum()))
    positives = max(1, int((y_true == 1).sum()))
    for threshold in thresholds:
        predicted = defect_score >= threshold
        tp, tn, fp, fn = confusion_counts(y_true, predicted.astype(int))
        fpr.append(fp / negatives)
        tpr.append(tp / positives)
    return np.asarray(fpr), np.asarray(tpr), thresholds


def run_analysis(df, metrics, mos_threshold):
    df["low_mos_label"] = (df["MOS"] < mos_threshold).astype(int)
    y_true = df["low_mos_label"].to_numpy()
    if len(np.unique(y_true)) != 2:
        raise ValueError("The selected MOS threshold must produce both label classes.")

    roc_rows, summaries = [], []
    for metric in metrics:
        defect_score = 100.0 - df[metric].to_numpy()
        fpr, tpr, thresholds = roc_points(y_true, defect_score)
        roc_auc = float(np.sum(np.diff(fpr) * (tpr[1:] + tpr[:-1]) / 2.0))
        best_idx = int(np.argmax(tpr - fpr))
        pred = (defect_score >= thresholds[best_idx]).astype(int)
        tp, tn, fp, fn = confusion_counts(y_true, pred)
        similarity_cutoff = 100.0 - float(thresholds[best_idx])
        summaries.append({
            "Metric": metric,
            "AUC": round(float(roc_auc), 4),
            "Youden_similarity_threshold_percent": round(similarity_cutoff, 4),
            "FPR": round(fp / (fp + tn), 4) if fp + tn else 0.0,
            "FNR": round(fn / (fn + tp), 4) if fn + tp else 0.0,
            "TP": tp, "TN": tn, "FP": fp, "FN": fn,
            "N": len(df), "MOS_threshold": mos_threshold,
            "Label_type": "MOS-derived perceptual-quality proxy",
        })
        for x, y, threshold in zip(fpr, tpr, thresholds):
            roc_rows.append({
                "Metric": metric, "FPR": round(float(x), 6),
                "TPR": round(float(y), 6),
                "Defect_score_threshold": round(float(threshold), 6),
            })

    roc_df = pd.DataFrame(roc_rows)
    summary_df = pd.DataFrame(summaries)
    roc_df.to_csv(OUTPUT_ROC, index=False)
    summary_df.to_csv(OUTPUT_SUMMARY, index=False)
    print(f"Saved ROC points: {OUTPUT_ROC.relative_to(ROOT)}")
    print(f"Saved metric summary: {OUTPUT_SUMMARY.relative_to(ROOT)}")
    print(summary_df.to_string(index=False))

    # TC11 uses the published scenario thresholds: DINOv2-Base >=70,
    # OpenCLIP >=65, and SSIM >=75. The staged form implements the same AND
    # policy while recording the first failed stage for diagnosis.
    required = {"DINOv2-Base", "OpenCLIP", "SSIM"}
    if required.issubset(df.columns):
        passed_semantic = (df["DINOv2-Base"] >= 70) & (df["OpenCLIP"] >= 65)
        passed_all = passed_semantic & (df["SSIM"] >= 75)
        predictions = (~passed_all).astype(int).to_numpy()
        tp, tn, fp, fn = confusion_counts(y_true, predictions)
        diagnostics = np.where(
            ~passed_semantic, "semantic stage failed",
            np.where(df["SSIM"] < 75, "structural stage failed", "pass")
        )
        combined = pd.DataFrame([{
            "Rule": "TC11 AND / staged equivalent",
            "DINOv2_Base_min_percent": 70,
            "OpenCLIP_min_percent": 65,
            "SSIM_min_percent": 75,
            "Pass_count": int(passed_all.sum()),
            "MOS_proxy_TP": tp, "MOS_proxy_TN": tn,
            "MOS_proxy_FP": fp, "MOS_proxy_FN": fn,
            "N": len(df), "MOS_threshold": mos_threshold,
            "Label_type": "MOS-derived perceptual-quality proxy, not software faults",
            "Staged_diagnostic_counts": "; ".join(
                f"{name}={int((diagnostics == name).sum())}"
                for name in ["semantic stage failed", "structural stage failed", "pass"]
            ),
        }])
        combined.to_csv(OUTPUT_COMBINED, index=False)
        print(f"Saved TC11 comparison: {OUTPUT_COMBINED.relative_to(ROOT)}")
    else:
        print("TC11 comparison skipped: DINOv2-Base, OpenCLIP, or SSIM score is missing.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mos-threshold", type=float, default=60.0,
                        help="MOS cutoff for the low-quality proxy label (default: 60).")
    args = parser.parse_args()
    try:
        df, metrics = prepare_data()
        run_analysis(df, metrics, args.mos_threshold)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
