import pandas as pd
import numpy as np
from scipy.stats import pearsonr, spearmanr, kendalltau
from scipy.optimize import curve_fit


def logistic4(x, b1, b2, b3, b4):
    """4-parametreli lojistik (kararlı fit): SSIM (x) -> MOS (y_hat)"""
    return b1 * (0.5 - 1.0 / (1.0 + np.exp(b2 * (x - b3)))) + b4 * x


def _find_col(cols, candidates):
    cl = [c.lower() for c in cols]
    for cand in candidates:
        if cand.lower() in cl:
            return cols[cl.index(cand.lower())]
    # kısmi eşleşme
    for cand in candidates:
        for i, c in enumerate(cl):
            if cand.lower() in c:
                return cols[i]
    return None


def _normalize_names(s: pd.Series) -> pd.Series:
    """Baş/son boşlukları sil, stringe çevir."""
    return s.astype(str).str.strip()


def compute_correlations_for_pairs(results_csv_path: str,
                                   mos_excel_path: str,
                                   return_merged: bool = False):
    """
    - results_csv_path: CSV (Ref, Karşıt, metrik sütunları: 'SSIM (%)', 'DINOv2-Base (%)', ...)
    - mos_excel_path  : Excel (Original Image Name, Distorted Image Name, Score/MOS/DMOS...)

    Dönüş:
      return_merged=False -> df_summary (PLCC, RMSE, SROCC, KROCC)
      return_merged=True  -> (df_summary, df_with_mos)  # df_with_mos: MOS ekli ilk tablo
    """
    # 1) Sonuç CSV
    df_res = pd.read_csv(results_csv_path, sep=';', encoding='utf-8-sig')
    res_cols = df_res.columns.tolist()
    ref_col_res = _find_col(res_cols, ['Ref', 'Original', 'Original Image Name', 'OriginalImageName'])
    kar_col_res = _find_col(res_cols, ['Karşıt', 'Karsit', 'Distorted', 'Distorted Image Name', 'DistortedImageName'])
    if ref_col_res is None or kar_col_res is None:
        raise ValueError("Sonuç CSV'sinde Ref/Karşıt sütunları bulunamadı.")

    # 2) MOS Excel
    df_mos = pd.read_excel(mos_excel_path)
    mos_cols = df_mos.columns.tolist()
    ref_col_mos = _find_col(mos_cols, ['Original Image Name', 'OriginalImageName', 'Original', 'Ref'])
    dis_col_mos = _find_col(mos_cols, ['Distorted Image Name', 'DistortedImageName', 'Distorted', 'Karşıt', 'Karsit'])
    mos_col     = _find_col(mos_cols, ['Score', 'MOS', 'DMOS', 'Label', 'Y'])
    if ref_col_mos is None or dis_col_mos is None or mos_col is None:
        raise ValueError("MOS Excel'de gerekli kolon(lar) bulunamadı (Original/Distorted/Score).")

    # 3) Normalize et
    df_res = df_res.copy()
    df_mos = df_mos.copy()
    df_res[ref_col_res] = _normalize_names(df_res[ref_col_res])
    df_res[kar_col_res] = _normalize_names(df_res[kar_col_res])
    df_mos[ref_col_mos] = _normalize_names(df_mos[ref_col_mos])
    df_mos[dis_col_mos] = _normalize_names(df_mos[dis_col_mos])

    # 4) Birbirini bulan satırların sıkı eşleştirmesi (inner merge)
    merged = pd.merge(
        df_res,
        df_mos[[ref_col_mos, dis_col_mos, mos_col]],
        left_on=[ref_col_res, kar_col_res],
        right_on=[ref_col_mos, dis_col_mos],
        how='inner'
    )
    if merged.empty:
        raise ValueError("Hiç eşleşen Ref–Karşıt çifti bulunamadı! İsimleri ve ayıracı (;) kontrol edin.")

    # MOS sütunu adı sabitle
    merged = merged.rename(columns={mos_col: 'MOS'})

    # 5) Korelasyonlar
    metric_cols = [c for c in df_res.columns if c not in [ref_col_res, kar_col_res]]
    records = []
    for m in metric_cols:
        vals_raw = pd.to_numeric(merged[m], errors='coerce')
        mos_vals = pd.to_numeric(merged['MOS'], errors='coerce')

        # SSIM yüzdelerini [0,1]'e çevir
        if m.lower().startswith('ssim'):
            x = vals_raw / 100.0
        else:
            x = vals_raw.astype(float)
        y = mos_vals.astype(float)

        mask = x.notna() & y.notna()
        if mask.sum() < 3:
            records.append({'Metric': m, 'RMSE': np.nan, 'PLCC': np.nan, 'SROCC': np.nan, 'KROCC': np.nan})
            continue

        # Sıra korelasyonları (eşlemesiz)
        srocc = spearmanr(x[mask], y[mask])[0]
        krocc = kendalltau(x[mask], y[mask])[0]

        # Lojistik fit (PLCC/RMSE için)
        try:
            xfit = x[mask].to_numpy()
            yfit = y[mask].to_numpy()
            p0 = [yfit.max() - yfit.min(), 10.0, np.median(xfit), yfit.min()]
            params, _ = curve_fit(logistic4, xfit, yfit, p0=p0, maxfev=20000)
            y_pred = logistic4(xfit, *params)
            plcc = pearsonr(y_pred, yfit)[0]
            rmse = float(np.sqrt(np.mean((y_pred - yfit) ** 2)))
        except Exception:
            # Fit başarısızsa doğrudan
            plcc = pearsonr(x[mask], y[mask])[0]
            rmse = float(np.sqrt(np.mean((x[mask] - y[mask]) ** 2)))

        records.append({
            'Metric': m,
            'RMSE': round(rmse, 4),
            'PLCC': round(plcc, 4),
            'SROCC': round(float(srocc), 4),
            'KROCC': round(float(krocc), 4),
        })

    df_summary = pd.DataFrame(records)[['Metric', 'RMSE', 'PLCC', 'SROCC', 'KROCC']]

    # 6) İlk tablo: MOS ekli tam sonuçlar
    # Kullanışlı kolon sırası: [Ref, Karşıt, metrikler..., MOS]
    keep_order = [ref_col_res, kar_col_res] + metric_cols + ['MOS']
    df_with_mos = merged[keep_order].copy()

    return (df_summary, df_with_mos) if return_merged else df_summary
