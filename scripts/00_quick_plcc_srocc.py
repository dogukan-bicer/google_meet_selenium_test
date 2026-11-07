#!/usr/bin/env python3
"""
Hızlı PLCC/SROCC Analizi — Mevcut results_dinov2.csv + Score_mos.xlsx
======================================================================
Bu script ML paketi kurmadan, sadece mevcut CSV sonuçlarını kullanarak
PLCC ve SROCC korelasyonlarını hesaplar.

Çalıştırma (sadece scipy + openpyxl gerekli):
  python scripts/00_quick_plcc_srocc.py

Çıktı:
  - dataset/nits_iqa/results/plcc_srocc_summary.csv
  - dataset/nits_iqa/results/plcc_srocc_by_distortion.csv
"""

import sys
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path

try:
    import numpy as np
except ImportError:
    print("[HATA] numpy kurun: pip install numpy --break-system-packages")
    sys.exit(1)
try:
    import pandas as pd
except ImportError:
    print("[HATA] pandas kurun: pip install pandas --break-system-packages")
    sys.exit(1)
try:
    from scipy.stats import pearsonr, spearmanr
except ImportError:
    print("[HATA] scipy kurun: pip install scipy --break-system-packages")
    sys.exit(1)
try:
    import openpyxl
except ImportError:
    print("[HATA] openpyxl kurun: pip install openpyxl --break-system-packages")
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "dataset" / "nits_iqa" / "results"

SCORES_CSV = RESULTS_DIR / "results_dinov2.csv"
MOS_FILE = RESULTS_DIR / "Score_mos.xlsx"
OUT_SUMMARY = RESULTS_DIR / "plcc_srocc_summary.csv"
OUT_BY_DIST = RESULTS_DIR / "plcc_srocc_by_distortion.csv"
OUT_BY_LEVEL = RESULTS_DIR / "plcc_srocc_by_level.csv"


def load_scores():
    """Mevcut sonuç CSV'sini yükler."""
    df = pd.read_csv(SCORES_CSV, sep=';')
    # Kolon adlarını normalize et
    df.columns = [c.strip() for c in df.columns]
    print(f"[i] Skorlar yüklendi: {len(df)} satır")
    print(f"    Kolonlar: {list(df.columns)}")
    return df


def load_mos():
    """MOS Excel dosyasını yükler."""
    df = pd.read_excel(MOS_FILE)
    df.columns = ['ref', 'que', 'MOS']
    # Başlık satırını çıkar
    df = df[df['que'] != 'Distorted Image Name'].copy()
    df['MOS'] = pd.to_numeric(df['MOS'], errors='coerce')
    print(f"[i] MOS yüklendi: {len(df)} satır")
    return df


def parse_distortion_level(que_name):
    """'I1D2L3.bmp' → (image_id=1, dist_id=2, level=3)"""
    import re
    m = re.match(r'I(\d+)D(\d+)L(\d+)', str(que_name))
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None, None, None


def compute_plcc_srocc(x, y):
    """PLCC ve SROCC hesapla."""
    valid = [(a, b) for a, b in zip(x, y) if pd.notna(a) and pd.notna(b)]
    if len(valid) < 5:
        return None, None, len(valid)
    xv, yv = zip(*valid)
    plcc, _ = pearsonr(xv, yv)
    srocc, _ = spearmanr(xv, yv)
    return round(plcc, 4), round(srocc, 4), len(valid)


def main():
    print("=" * 70)
    print("Hızlı PLCC/SROCC Analizi — Mevcut Sonuçlar")
    print("=" * 70)

    # Veri yükle
    scores_df = load_scores()
    mos_df = load_mos()

    # Kolon adı eşleştirmesi
    # CSV: Ref;Karşıt;DINOv2-Base (%);DINOv2-Large (%);Dists (%);SSIM (%);OpenCLIP (%)
    ref_col = scores_df.columns[0]  # 'Ref'
    que_col = scores_df.columns[1]  # 'Karşıt'

    # MOS ile birleştir
    merged = scores_df.merge(
        mos_df.rename(columns={'ref': ref_col, 'que': que_col}),
        on=[ref_col, que_col],
        how='left'
    )

    # Bozulma türü ve seviyesi parse et
    parsed = merged[que_col].apply(lambda x: parse_distortion_level(x))
    merged['image_id'] = parsed.apply(lambda t: t[0])
    merged['dist_id'] = parsed.apply(lambda t: t[1])
    merged['level'] = parsed.apply(lambda t: t[2])

    print(f"\n[i] Birleştirildi: {len(merged)} satır, MOS var: {merged['MOS'].notna().sum()}")

    # Metrik kolonları bul
    metric_cols = {
        'DINOv2-Base': None,
        'DINOv2-Large': None,
        'DISTS': None,
        'SSIM': None,
        'OpenCLIP': None
    }
    for col in merged.columns:
        if 'DINOv2-Base' in col or 'Base' in col and 'DINO' in col:
            metric_cols['DINOv2-Base'] = col
        elif 'DINOv2-Large' in col or 'Large' in col and 'DINO' in col:
            metric_cols['DINOv2-Large'] = col
        elif 'Dists' in col or 'DISTS' in col.upper():
            metric_cols['DISTS'] = col
        elif 'SSIM' in col.upper():
            metric_cols['SSIM'] = col
        elif 'OpenCLIP' in col or 'CLIP' in col.upper():
            metric_cols['OpenCLIP'] = col

    print(f"\n[i] Metrik kolon eşleştirmesi:")
    for m, c in metric_cols.items():
        print(f"    {m}: {c}")

    available = {m: c for m, c in metric_cols.items() if c is not None}

    # --- Genel PLCC/SROCC ---
    print("\n--- Genel Korelasyon (tüm 405 görüntü) ---")
    summary_rows = []
    for metric, col in available.items():
        plcc, srocc, n = compute_plcc_srocc(merged[col].values, merged['MOS'].values)
        summary_rows.append({'Metric': metric, 'PLCC': plcc, 'SROCC': srocc, 'N': n})
        print(f"  {metric:20s}: PLCC={plcc}  SROCC={srocc}  (N={n})")

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(OUT_SUMMARY, index=False)
    print(f"[✓] Özet kaydedildi: {OUT_SUMMARY}")

    # --- Bozulma türüne göre PLCC/SROCC ---
    print("\n--- Bozulma Türüne Göre Korelasyon ---")
    dist_rows = []
    for dist_id in sorted(merged['dist_id'].dropna().unique()):
        sub = merged[merged['dist_id'] == dist_id]
        row = {'Distortion_ID': int(dist_id)}
        for metric, col in available.items():
            plcc, srocc, n = compute_plcc_srocc(sub[col].values, sub['MOS'].values)
            row[f'{metric}_PLCC'] = plcc
            row[f'{metric}_SROCC'] = srocc
        row['N'] = len(sub)
        dist_rows.append(row)
        plcc_vals = [v for k, v in row.items() if 'PLCC' in k and v is not None]
        print(f"  Bozulma D{int(dist_id)}: N={len(sub)}, PLCC_ortalama={np.mean(plcc_vals):.4f}")

    dist_df = pd.DataFrame(dist_rows)
    dist_df.to_csv(OUT_BY_DIST, index=False)
    print(f"[✓] Bozulma türü bazlı analiz kaydedildi: {OUT_BY_DIST}")

    # --- Şiddet seviyesine göre PLCC/SROCC ---
    print("\n--- Şiddet Seviyesine Göre Korelasyon ---")
    level_rows = []
    for level in sorted(merged['level'].dropna().unique()):
        sub = merged[merged['level'] == level]
        row = {'Level': int(level)}
        for metric, col in available.items():
            plcc, srocc, n = compute_plcc_srocc(sub[col].values, sub['MOS'].values)
            row[f'{metric}_PLCC'] = plcc
            row[f'{metric}_SROCC'] = srocc
        row['N'] = len(sub)
        level_rows.append(row)
        plcc_vals = [v for k, v in row.items() if 'PLCC' in k and v is not None]
        print(f"  Seviye L{int(level)}: N={len(sub)}, PLCC_ortalama={np.mean(plcc_vals):.4f}")

    level_df = pd.DataFrame(level_rows)
    level_df.to_csv(OUT_BY_LEVEL, index=False)
    print(f"[✓] Seviye bazlı analiz kaydedildi: {OUT_BY_LEVEL}")

    print("\n[✓] Hızlı analiz tamamlandı!")
    print(f"\nÇıktılar: {RESULTS_DIR}")


if __name__ == '__main__':
    main()
