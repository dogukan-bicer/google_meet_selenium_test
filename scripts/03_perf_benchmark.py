#!/usr/bin/env python3
"""
Deney 3: Model Bazında Performans Ölçümü
=========================================
Hedef:
  - Her modelin gecikmesi: medyan ve p95 (ms)
  - GPU belleği (MB) ve GPU kullanımı (%)
  - Yük testi: 1, 2, 5, 10 eşzamanlı istek

Çalıştırma:
  python scripts/03_perf_benchmark.py

Çıktı:
  - results/perf_benchmark.csv
  - results/perf_load_test.csv
"""

import os
import sys
import time
import threading
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
QUE_DIR = REPO_ROOT / "dataset" / "nits_iqa" / "que"
REF_DIR = REPO_ROOT / "dataset" / "nits_iqa" / "ref"
RESULTS_DIR = REPO_ROOT / "dataset" / "nits_iqa" / "results"
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT_BENCH = RESULTS_DIR / "perf_benchmark.csv"
OUTPUT_LOAD = RESULTS_DIR / "perf_load_test.csv"

# Tekrar sayısı
N_WARMUP = 2
N_RUNS = 10

# --- GPU izleme ---
def get_gpu_info():
    """GPU belleği ve kullanımını döner (MB, %)."""
    try:
        import torch
        if torch.cuda.is_available():
            mem_alloc = torch.cuda.memory_allocated() / 1024**2
            mem_reserved = torch.cuda.memory_reserved() / 1024**2
            return mem_alloc, mem_reserved
    except Exception:
        pass
    return 0.0, 0.0


def get_gpu_util():
    """GPU kullanım yüzdesi."""
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        return float(util.gpu)
    except Exception:
        pass
    return 0.0


# --- Model yükleyici ---
def load_all_models():
    """Tüm modelleri yükler ve (name, func, device) tuple listesi döner."""
    models = []

    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[i] Device: {device}")
    except ImportError:
        device = "cpu"
        print("[!] PyTorch bulunamadı, CPU varsayıldı")

    # --- SSIM ---
    try:
        from skimage.metrics import structural_similarity as _ssim

        def ssim_func(ref_path, que_path):
            size = (400, 400)
            img1 = np.array(Image.open(ref_path).convert('L').resize(size), dtype=np.float32)
            img2 = np.array(Image.open(que_path).convert('L').resize(size), dtype=np.float32)
            return _ssim(img1, img2, data_range=255)

        models.append(('SSIM', ssim_func, 'cpu'))
        print("[✓] SSIM hazır")
    except Exception as e:
        print(f"[✗] SSIM: {e}")

    # --- DINOv2-Base ---
    try:
        import torch
        import torch.nn.functional as F
        from transformers import AutoImageProcessor, AutoModel

        proc = AutoImageProcessor.from_pretrained('facebook/dinov2-base')
        model = AutoModel.from_pretrained('facebook/dinov2-base').to(device).eval()

        def dinov2_base_func(ref_path, que_path):
            img1 = Image.open(ref_path).convert('RGB')
            img2 = Image.open(que_path).convert('RGB')
            inputs = proc(images=[img1, img2], return_tensors="pt").to(device)
            with torch.no_grad():
                out = model(**inputs)
                feats = out.last_hidden_state[:, 0, :]
            return F.cosine_similarity(feats[0], feats[1], dim=0).item()

        models.append(('DINOv2-Base', dinov2_base_func, device))
        print("[✓] DINOv2-Base hazır")
    except Exception as e:
        print(f"[✗] DINOv2-Base: {e}")

    # --- DINOv2-Large ---
    try:
        import torch
        import torch.nn.functional as F
        from transformers import AutoImageProcessor, AutoModel

        proc_l = AutoImageProcessor.from_pretrained('facebook/dinov2-large')
        model_l = AutoModel.from_pretrained('facebook/dinov2-large').to(device).eval()

        def dinov2_large_func(ref_path, que_path):
            img1 = Image.open(ref_path).convert('RGB')
            img2 = Image.open(que_path).convert('RGB')
            inputs = proc_l(images=[img1, img2], return_tensors="pt").to(device)
            with torch.no_grad():
                out = model_l(**inputs)
                feats = out.last_hidden_state[:, 0, :]
            return F.cosine_similarity(feats[0], feats[1], dim=0).item()

        models.append(('DINOv2-Large', dinov2_large_func, device))
        print("[✓] DINOv2-Large hazır")
    except Exception as e:
        print(f"[✗] DINOv2-Large: {e}")

    # --- OpenCLIP ---
    try:
        import torch
        import torch.nn.functional as F
        import open_clip

        model_clip, _, preprocess_clip = open_clip.create_model_and_transforms(
            'ViT-B-32', pretrained='openai'
        )
        model_clip = model_clip.to(device).eval()

        def openclip_func(ref_path, que_path):
            img1 = preprocess_clip(Image.open(ref_path).convert('RGB')).unsqueeze(0).to(device)
            img2 = preprocess_clip(Image.open(que_path).convert('RGB')).unsqueeze(0).to(device)
            with torch.no_grad():
                f1 = model_clip.encode_image(img1)
                f2 = model_clip.encode_image(img2)
            f1 = f1 / f1.norm(dim=-1, keepdim=True)
            f2 = f2 / f2.norm(dim=-1, keepdim=True)
            return F.cosine_similarity(f1, f2, dim=-1).item()

        models.append(('OpenCLIP', openclip_func, device))
        print("[✓] OpenCLIP hazır (ViT-B-32)")
    except Exception as e:
        print(f"[✗] OpenCLIP: {e}")

    # --- DISTS ---
    try:
        import torch
        import torchvision.transforms as T
        from DISTS_pytorch import DISTS

        dists_model = DISTS().to(device).eval()
        transform = T.Compose([T.Resize((400, 400)), T.ToTensor()])

        def dists_func(ref_path, que_path):
            img1 = transform(Image.open(ref_path).convert('RGB')).unsqueeze(0).to(device)
            img2 = transform(Image.open(que_path).convert('RGB')).unsqueeze(0).to(device)
            with torch.no_grad():
                return dists_model(img1, img2).item()

        models.append(('DISTS', dists_func, device))
        print("[✓] DISTS hazır")
    except Exception as e:
        print(f"[✗] DISTS: {e}")

    return models


def benchmark_model(name, func, device, ref_path, que_path, n_warmup=2, n_runs=10):
    """Tekil model için gecikme ölç."""
    # Warm-up
    for _ in range(n_warmup):
        func(ref_path, que_path)

    # Ölçüm
    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        func(ref_path, que_path)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)  # ms

    mem_alloc, mem_reserved = get_gpu_info()
    gpu_util = get_gpu_util()

    return {
        'Model': name,
        'Device': device,
        'Median_ms': round(np.median(times), 2),
        'P95_ms': round(np.percentile(times, 95), 2),
        'Mean_ms': round(np.mean(times), 2),
        'Std_ms': round(np.std(times), 2),
        'Min_ms': round(np.min(times), 2),
        'Max_ms': round(np.max(times), 2),
        'GPU_Mem_Alloc_MB': round(mem_alloc, 2),
        'GPU_Mem_Reserved_MB': round(mem_reserved, 2),
        'GPU_Util_pct': round(gpu_util, 2),
        'N_runs': n_runs
    }


def load_test(name, func, ref_path, que_path, n_concurrent_list=[1, 2, 5, 10]):
    """Farklı eşzamanlı istek sayılarında gecikme testi."""
    results = []
    for n in n_concurrent_list:
        times = []
        errors = 0

        with ThreadPoolExecutor(max_workers=n) as executor:
            futures = [
                executor.submit(lambda: (time.perf_counter(), func(ref_path, que_path), time.perf_counter()))
                for _ in range(n)
            ]
            for f in futures:
                try:
                    t0, _, t1 = f.result()
                    times.append((t1 - t0) * 1000)
                except Exception:
                    errors += 1

        if times:
            results.append({
                'Model': name,
                'Concurrent': n,
                'Median_ms': round(np.median(times), 2),
                'P95_ms': round(np.percentile(times, 95), 2),
                'Max_ms': round(np.max(times), 2),
                'Errors': errors
            })
            print(f"    n={n:2d}: medyan={np.median(times):.1f}ms  p95={np.percentile(times,95):.1f}ms")

    return results


def main():
    print("=" * 70)
    print("Deney 3: Model Bazında Performans Ölçümü")
    print("=" * 70)

    # Test görüntüsü seç
    que_files = list(QUE_DIR.glob("*.bmp"))
    ref_files = list(REF_DIR.glob("*.bmp"))

    if not que_files or not ref_files:
        print(f"[HATA] Görüntü bulunamadı: {QUE_DIR}")
        sys.exit(1)

    # Ilk çift
    que_path = str(que_files[0])
    ref_name = f"I{que_path.split('I')[1][0]}.bmp"
    ref_path = str(REF_DIR / ref_name)
    print(f"\n[i] Test çifti: {Path(ref_path).name} vs {Path(que_path).name}")

    # Modelleri yükle
    models = load_all_models()
    if not models:
        print("[HATA] Hiçbir model yüklenemedi!")
        sys.exit(1)

    # Bireysel benchmark
    print(f"\n--- Tekil Gecikme Ölçümü (N_warmup={N_WARMUP}, N_runs={N_RUNS}) ---")
    bench_rows = []
    for name, func, device in models:
        print(f"  Ölçülüyor: {name}...")
        try:
            row = benchmark_model(name, func, device, ref_path, que_path, N_WARMUP, N_RUNS)
            bench_rows.append(row)
            print(f"    Medyan={row['Median_ms']}ms  P95={row['P95_ms']}ms  GPU={row['GPU_Mem_Alloc_MB']}MB")
        except Exception as e:
            print(f"    [!] Hata: {e}")

    bench_df = pd.DataFrame(bench_rows)
    bench_df.to_csv(OUTPUT_BENCH, index=False)
    print(f"\n[✓] Benchmark sonuçları kaydedildi: {OUTPUT_BENCH}")
    print("\n--- Özet Tablo ---")
    if not bench_df.empty:
        print(bench_df[['Model', 'Device', 'Median_ms', 'P95_ms', 'GPU_Mem_Alloc_MB']].to_string(index=False))

    # Yük testi
    print(f"\n--- Yük Testi (eşzamanlı: 1, 2, 5, 10) ---")
    load_rows = []
    for name, func, device in models:
        print(f"\n  Model: {name}")
        try:
            rows = load_test(name, func, ref_path, que_path, [1, 2, 5, 10])
            load_rows.extend(rows)
        except Exception as e:
            print(f"  [!] Hata: {e}")

    load_df = pd.DataFrame(load_rows)
    load_df.to_csv(OUTPUT_LOAD, index=False)
    print(f"\n[✓] Yük testi sonuçları kaydedildi: {OUTPUT_LOAD}")

    # Yük testi grafiği
    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 6))
        for model_name in load_df['Model'].unique():
            sub = load_df[load_df['Model'] == model_name]
            ax.plot(sub['Concurrent'], sub['Median_ms'], marker='o', label=model_name)

        ax.set_xlabel('Eşzamanlı İstek Sayısı')
        ax.set_ylabel('Gecikme (ms)')
        ax.set_title('Yük Testi — Model Bazında Gecikme')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(RESULTS_DIR / "load_test.png", dpi=150)
        plt.close()
        print(f"[✓] Yük testi grafiği kaydedildi: {RESULTS_DIR / 'load_test.png'}")
    except ImportError:
        print("[!] matplotlib yüklü değil, grafik atlanıyor")

    print("\n[✓] Deney 3 tamamlandı!")


if __name__ == '__main__':
    main()
