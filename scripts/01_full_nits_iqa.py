#!/usr/bin/env python3
"""
Deney 1: Tüm NITS-IQA Veri Setinde 5 Metriği Çalıştırma
=========================================================
Hedef: 405 görüntü çifti için DINOv2-Base, DINOv2-Large, DISTS, SSIM, OpenCLIP
       skorlarını hesapla; MOS ile PLCC/SROCC korelasyonlarını raporla.

Çıktı:
  - results/full_nits_iqa_scores.csv
  - results/full_nits_iqa_plcc_srocc.csv
  - results/full_nits_iqa_by_distortion.csv
"""

import os
import sys
import time
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import pearsonr, spearmanr

# --- Path setup ---
REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = REPO_ROOT / "dataset" / "nits_iqa"
REF_DIR = DATASET_DIR / "ref"
QUE_DIR = DATASET_DIR / "que"
MOS_FILE = DATASET_DIR / "results" / "Score_mos.xlsx"
RESULTS_DIR = DATASET_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT_CSV = RESULTS_DIR / "full_nits_iqa_scores.csv"
OUTPUT_CORR = RESULTS_DIR / "full_nits_iqa_plcc_srocc.csv"
OUTPUT_BY_DIST = RESULTS_DIR / "full_nits_iqa_by_distortion.csv"


# =============================================================================
# Metrik fonksiyonları
# =============================================================================

def load_metrics():
    """Tüm modelleri yükler ve metric fonksiyonlarını döner."""
    metrics = {}

    # SSIM (her zaman çalışır)
    try:
        from PIL import Image
        from skimage.metrics import structural_similarity as _ssim
        import numpy as _np

        def compute_ssim(ref_path, que_path):
            size = (400, 400)
            img1 = Image.open(ref_path).convert('L').resize(size)
            img2 = Image.open(que_path).convert('L').resize(size)
            arr1 = _np.array(img1, dtype=_np.float32)
            arr2 = _np.array(img2, dtype=_np.float32)
            score = _ssim(arr1, arr2, data_range=255)
            return float(score)

        metrics['SSIM'] = compute_ssim
        print("[✓] SSIM yüklendi")
    except Exception as e:
        print(f"[✗] SSIM yüklenemedi: {e}")

    # DINOv2-Base & DINOv2-Large
    try:
        import torch
        import torch.nn.functional as F
        from PIL import Image
        from transformers import AutoImageProcessor, AutoModel

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[i] Torch device: {device}")

        # DINOv2-Base
        proc_base = AutoImageProcessor.from_pretrained('facebook/dinov2-base')
        model_base = AutoModel.from_pretrained('facebook/dinov2-base').to(device).eval()

        # DINOv2-Large
        proc_large = AutoImageProcessor.from_pretrained('facebook/dinov2-large')
        model_large = AutoModel.from_pretrained('facebook/dinov2-large').to(device).eval()

        def _dinov2_sim(proc, model, ref_path, que_path, device):
            img1 = Image.open(ref_path).convert('RGB')
            img2 = Image.open(que_path).convert('RGB')
            inputs = proc(images=[img1, img2], return_tensors="pt").to(device)
            with torch.no_grad():
                out = model(**inputs)
                feats = out.last_hidden_state[:, 0, :]  # CLS token
            sim = F.cosine_similarity(feats[0], feats[1], dim=0).item()
            return float(sim)

        metrics['DINOv2-Base'] = lambda r, q: _dinov2_sim(proc_base, model_base, r, q, device)
        metrics['DINOv2-Large'] = lambda r, q: _dinov2_sim(proc_large, model_large, r, q, device)
        print("[✓] DINOv2-Base ve DINOv2-Large yüklendi")
    except Exception as e:
        print(f"[✗] DINOv2 yüklenemedi: {e}")

    # OpenCLIP (ViT-B-32, OpenAI weights)
    try:
        import torch
        import torch.nn.functional as F
        import open_clip
        from PIL import Image

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_clip, _, preprocess_clip = open_clip.create_model_and_transforms(
            'ViT-B-32', pretrained='openai'
        )
        model_clip = model_clip.to(device).eval()

        def compute_openclip(ref_path, que_path):
            img1 = Image.open(ref_path).convert('RGB')
            img2 = Image.open(que_path).convert('RGB')
            t1 = preprocess_clip(img1).unsqueeze(0).to(device)
            t2 = preprocess_clip(img2).unsqueeze(0).to(device)
            with torch.no_grad():
                f1 = model_clip.encode_image(t1)
                f2 = model_clip.encode_image(t2)
            f1 = f1 / f1.norm(dim=-1, keepdim=True)
            f2 = f2 / f2.norm(dim=-1, keepdim=True)
            sim = F.cosine_similarity(f1, f2, dim=-1).item()
            return float(sim)

        metrics['OpenCLIP'] = compute_openclip
        print("[✓] OpenCLIP yüklendi (ViT-B-32 / OpenAI weights)")
    except Exception as e:
        print(f"[✗] OpenCLIP yüklenemedi: {e}")

    # DISTS
    try:
        import torch
        import torchvision.transforms as T
        from PIL import Image
        from DISTS_pytorch import DISTS

        device = "cuda" if torch.cuda.is_available() else "cpu"
        dists_model = DISTS().to(device).eval()
        transform_dists = T.Compose([T.Resize((400, 400)), T.ToTensor()])

        def compute_dists(ref_path, que_path):
            img1 = transform_dists(Image.open(ref_path).convert('RGB')).unsqueeze(0).to(device)
            img2 = transform_dists(Image.open(que_path).convert('RGB')).unsqueeze(0).to(device)
            with torch.no_grad():
                dist = dists_model(img1, img2).item()
            # DISTS mesafe → benzerliğe çevir (0=aynı, 1=tamamen farklı)
            return float(1.0 - min(dist, 1.0))

        metrics['DISTS'] = compute_dists
        print("[✓] DISTS yüklendi")
    except Exception as e:
        print(f"[✗] DISTS yüklenemedi: {e}")

    return metrics


def parse_filename(fname):
    """
    'I1D2L3.bmp' → {'image_id': 1, 'distortion_id': 2, 'level': 3}
    'I1.bmp' → referans
    """
    name = Path(fname).stem  # 'I1D2L3'
    try:
        # Karmaşık bozulma: I{i}D{d}L{l}
        import re
        m = re.match(r'I(\d+)D(\d+)L(\d+)', name)
        if m:
            return {
                'image_id': int(m.group(1)),
                'distortion_id': int(m.group(2)),
                'level': int(m.group(3))
            }
    except Exception:
        pass
    return None


def load_mos(mos_file):
    """
    Score_mos.xlsx dosyasını okur.
    Beklenen format: kolonlar 'FileName', 'MOS' (ya da benzer)
    """
    try:
        df = pd.read_excel(mos_file)
        if {"Original Image Name", "Distorted Image Name", "Score"}.issubset(df.columns):
            df = df.rename(columns={
                "Original Image Name": "ref",
                "Distorted Image Name": "que",
                "Score": "MOS",
            })[["ref", "que", "MOS"]]
        elif len(df.columns) >= 3:
            df = df.iloc[:, :3].copy()
            df.columns = ["ref", "que", "MOS"]
        else:
            raise ValueError("MOS workbook must contain reference, distorted-image, and score columns")
        df["ref"] = df["ref"].astype(str).str.strip()
        df["que"] = df["que"].astype(str).str.strip()
        df["MOS"] = pd.to_numeric(df["MOS"], errors="coerce")
        df = df.dropna(subset=["MOS"])
        print(f"[i] MOS dosyası yüklendi: {df.shape[0]} satır")
        return df
    except Exception as e:
        print(f"[✗] MOS dosyası okunamadı: {e}")
        return None


# =============================================================================
# Ana çalıştırma
# =============================================================================

def main():
    print("=" * 70)
    print("Deney 1: Tüm NITS-IQA Veri Setinde Metrik Hesaplama")
    print("=" * 70)

    # Modelleri yükle
    metrics = load_metrics()
    if not metrics:
        print("[HATA] Hiçbir metrik yüklenemedi! requirements_full.txt kurulumunu yapın.")
        sys.exit(1)

    metric_names = list(metrics.keys())
    print(f"\n[i] Çalışacak metrikler: {metric_names}")

    # MOS verisi
    mos_df = load_mos(MOS_FILE)

    # Tüm que görüntülerini bul
    que_files = sorted(QUE_DIR.glob("*.bmp"))
    print(f"\n[i] {len(que_files)} bozulmuş görüntü bulundu")

    # Sonuçları topla
    rows = []
    total = len(que_files)

    for idx, que_path in enumerate(que_files, 1):
        info = parse_filename(que_path.name)
        if info is None:
            print(f"  [!] Parse edilemedi: {que_path.name}")
            continue

        # Referans dosyasını bul
        ref_name = f"I{info['image_id']}.bmp"
        ref_path = REF_DIR / ref_name
        if not ref_path.exists():
            print(f"  [!] Referans bulunamadı: {ref_name}")
            continue

        row = {
            'ref': ref_name,
            'que': que_path.name,
            'image_id': info['image_id'],
            'distortion_id': info['distortion_id'],
            'level': info['level'],
        }

        # MOS değerini bul
        if mos_df is not None:
            match = mos_df[
                (mos_df["ref"].str.casefold() == ref_name.casefold())
                & (mos_df["que"].str.casefold() == que_path.name.casefold())
            ]
            if not match.empty:
                row["MOS"] = float(match["MOS"].iloc[0])

        # Her metriği hesapla
        for mname, mfunc in metrics.items():
            try:
                score = mfunc(str(ref_path), str(que_path))
                row[mname] = round(score, 6)
            except Exception as e:
                print(f"  [!] {mname} hatası ({que_path.name}): {e}")
                row[mname] = None

        rows.append(row)

        # İlerleme
        if idx % 50 == 0 or idx == total:
            print(f"  [{idx}/{total}] {que_path.name} işlendi")

    # DataFrame oluştur ve kaydet
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n[✓] Skorlar kaydedildi: {OUTPUT_CSV}")

    # PLCC / SROCC hesapla
    print("\n--- Korelasyon Analizi (MOS ile) ---")
    if 'MOS' in df.columns and df['MOS'].notna().sum() > 0:
        corr_rows = []
        for mname in metric_names:
            if mname not in df.columns:
                continue
            valid = df[[mname, 'MOS']].dropna()
            if len(valid) < 10:
                continue
            plcc, p1 = pearsonr(valid[mname], valid['MOS'])
            srocc, p2 = spearmanr(valid[mname], valid['MOS'])
            corr_rows.append({
                'Metric': mname,
                'PLCC': round(plcc, 4),
                'PLCC_p': round(p1, 4),
                'SROCC': round(srocc, 4),
                'SROCC_p': round(p2, 4),
                'N': len(valid)
            })
            print(f"  {mname:20s}: PLCC={plcc:.4f}  SROCC={srocc:.4f}  (N={len(valid)})")

        corr_df = pd.DataFrame(corr_rows)
        corr_df.to_csv(OUTPUT_CORR, index=False)
        print(f"[✓] Korelasyonlar kaydedildi: {OUTPUT_CORR}")

        # Bozulma türüne göre ayrı analiz
        print("\n--- Bozulma Türüne Göre PLCC/SROCC ---")
        dist_rows = []
        for dist_id in sorted(df['distortion_id'].unique()):
            sub = df[df['distortion_id'] == dist_id]
            for mname in metric_names:
                if mname not in sub.columns:
                    continue
                valid = sub[[mname, 'MOS']].dropna()
                if len(valid) < 5:
                    continue
                plcc, _ = pearsonr(valid[mname], valid['MOS'])
                srocc, _ = spearmanr(valid[mname], valid['MOS'])
                dist_rows.append({
                    'Distortion_ID': dist_id,
                    'Metric': mname,
                    'PLCC': round(plcc, 4),
                    'SROCC': round(srocc, 4),
                    'N': len(valid)
                })
        dist_df = pd.DataFrame(dist_rows)
        dist_df.to_csv(OUTPUT_BY_DIST, index=False)
        print(f"[✓] Bozulma türü bazlı analiz kaydedildi: {OUTPUT_BY_DIST}")
    else:
        print("[!] MOS verisi bulunamadı veya eşleştirilemedi.")
        print("    MOS Excel dosyasını kontrol edin:", MOS_FILE)
        print("\n--- Mevcut verilerle istatistik ---")
        for mname in metric_names:
            if mname in df.columns:
                print(f"  {mname}: mean={df[mname].mean():.4f}, std={df[mname].std():.4f}")

    print("\n[✓] Deney 1 tamamlandı!")
    print(f"    Çıktılar: {RESULTS_DIR}")


if __name__ == '__main__':
    main()
