# -----------------------------
# Görüntü kalitesi testi
# -----------------------------

def compare_last_two_screenshots(log_func):
    """
    DINOv2 kullanarak son iki ekran görüntüsünü karşılaştırır.
    Hem eski (tek float) hem yeni (tuple) return formatlarını destekler.
    """
    try:
        # Son iki .png dosyasını al
        pngs = sorted(
            [f for f in os.listdir('.') if f.endswith('.png')],
            key=os.path.getmtime, reverse=True
        )[:2]
        if len(pngs) < 2:
            return None, "En az iki PNG gerekli!"

        ip1, ip2 = pngs[0].split('_')[0], pngs[1].split('_')[0]
        if ip1 == ip2:
            return None, "Aynı IP’den karşılaştırılamaz!"
        # Burada artık dönüş tipine göre ayrım yapıyoruz:
        ret = compare_image_files_dinov2(pngs[0], pngs[1])
        if isinstance(ret, tuple):
            # Yeni API: (similarity, error)
            similarity, error = ret
        else:
            # Eski API: sadece similarity (float)
            similarity, error = ret, None
        if error:
            return None, error
        return similarity, (pngs[0], pngs[1])
    except Exception as e:
        log_func(f"DINOv2 hatası: {e}")
        return None, str(e)

import torch
import torch.nn.functional as F
from PIL import Image
import open_clip

# Device setup
_device = "cuda" if torch.cuda.is_available() else "cpu"

# Load OpenCLIP model and preprocessing transforms
# Here using ViT-B-32 architecture with OpenAI-pretrained weights
_model_openclip, _, _preprocess = open_clip.create_model_and_transforms(
    model_name="ViT-B-32", pretrained="openai"
)
_model_openclip = _model_openclip.to(_device).eval()

# Function to compare two image files using OpenCLIP
def compare_image_files_openclip(img1_path: str, img2_path: str) -> float:
    """
    Takes two image file paths, extracts features via OpenCLIP,
    and returns cosine similarity as a percentage between 0 and 100.
    """
    # Load and preprocess images
    img1 = Image.open(img1_path).convert("RGB")
    img2 = Image.open(img2_path).convert("RGB")
    tensor1 = _preprocess(img1).unsqueeze(0).to(_device)
    tensor2 = _preprocess(img2).unsqueeze(0).to(_device)

    # Extract features
    with torch.no_grad():
        feat1 = _model_openclip.encode_image(tensor1)
        feat2 = _model_openclip.encode_image(tensor2)

    # Normalize features
    feat1 = feat1 / feat1.norm(dim=-1, keepdim=True)
    feat2 = feat2 / feat2.norm(dim=-1, keepdim=True)

    # Compute cosine similarity
    sim = F.cosine_similarity(feat1, feat2, dim=-1).item()
    # Convert to [0, 100]
    similarity_percent = max(sim * 100, 0.0)
    return similarity_percent

# Example usage:
# print(compare_image_files_openclip("path/to/img1.jpg", "path/to/img2.jpg"))


import torch
import torch.nn.functional as F
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
# Cihaz ayarı
_device = "cuda" if torch.cuda.is_available() else "cpu"
# DINOv2 model ve işlemcisi (BASE sürüm)
_processor = AutoImageProcessor.from_pretrained('facebook/dinov2-large')
_model = AutoModel.from_pretrained('facebook/dinov2-large').to(_device)

# Yardımcı fonksiyon (mevcut compare_last_two_screenshots’dan ayırıyoruz)
def compare_image_files_dinov2(img1_path, img2_path) -> float:
    """
    İki dosya yolu alır, DINOv2 ile özellik çıkarıp kosinüs benzerliği döner.
    Dönen değer 0-100 arası normalize edilmiş yüzde.
    """
    img1 = Image.open(img1_path).convert('RGB')
    img2 = Image.open(img2_path).convert('RGB')
    inputs = _processor(images=[img1, img2], return_tensors="pt").to(_device)
    with torch.no_grad():
        outputs = _model(**inputs)
        feats = outputs.last_hidden_state[:, 0, :]
    sim = F.cosine_similarity(feats[0], feats[1], dim=0).item()
    return max(sim * 100, 0)

# DINOv2 model ve işlemcisi (BASE sürüm)
_processor_base = AutoImageProcessor.from_pretrained('facebook/dinov2-base')
_model_base = AutoModel.from_pretrained('facebook/dinov2-base').to(_device)
# Yardımcı fonksiyon (mevcut compare_last_two_screenshots’dan ayırıyoruz)
def compare_image_files_dinov2_base(img1_path, img2_path) -> float:
    """
    İki dosya yolu alır, DINOv2 ile özellik çıkarıp kosinüs benzerliği döner.
    Dönen değer 0-100 arası normalize edilmiş yüzde.
    """
    img1 = Image.open(img1_path).convert('RGB')
    img2 = Image.open(img2_path).convert('RGB')
    inputs = _processor_base(images=[img1, img2], return_tensors="pt").to(_device)
    with torch.no_grad():
        outputs = _model_base(**inputs)
        feats = outputs.last_hidden_state[:, 0, :]
    sim = F.cosine_similarity(feats[0], feats[1], dim=0).item()
    return max(sim * 100, 0)



from DISTS_pytorch import DISTS
import torch
import torchvision.transforms as T
from PIL import Image
import os


# Cihaz ayarı
device = "cuda" if torch.cuda.is_available() else "cpu"

# DISTS metriğini yükle
dists = DISTS().to(device).eval()

# Önişleme: Sabit boyut ve [0–1] normalizasyon
transform = T.Compose([
    T.Resize((400, 400)),
    T.ToTensor(),          # [0,1] arası
])


def compare_image_files_dists(img1_path: str, img2_path: str) -> float:
    """
    İki görüntüyü DISTS ile kıyaslar.
    Dönen değer 0–100 arası normalize edilmiş benzerlik yüzdesi.
    """
    # Görselleri yükle ve tensor’a dönüştür
    img1 = transform(Image.open(img1_path).convert("RGB")) \
               .unsqueeze(0).to(device)  # [1,3,256,256]
    img2 = transform(Image.open(img2_path).convert("RGB")) \
               .unsqueeze(0).to(device)

    # DISTS mesafesini hesapla (0–1 arası)
    with torch.no_grad():
        dist = dists(img1, img2).item()

    # Mesafeyi benzerliğe çevir: dist=0→100, dist=1→0
    sim_pct = max((1.0 - min(dist, 1.0)) * 100.0, 0.0)
    return sim_pct


import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

def compare_image_files_ssim(img1_path, img2_path) -> float:
    """
    İki görüntü dosya yolunu alır, SSIM (Structural Similarity Index) ile karşılaştırır
    ve 0–100 arası normalize edilmiş SSIM yüzdesini döner.
    """
    # Görüntüleri aç, griye çevir ve aynı boyuta getir
    size = (600, 600)
    img1 = Image.open(img1_path).convert('L').resize(size)
    img2 = Image.open(img2_path).convert('L').resize(size)

    # NumPy dizilerine dönüştür
    arr1 = np.array(img1, dtype=np.float32)
    arr2 = np.array(img2, dtype=np.float32)

    # SSIM hesapla (0–1 arası değer döner)
    score = ssim(arr1, arr2, data_range=255)

    # 0–1 arası değeri 0–100 arası yüzdeye çevir
    return max(score * 100, 0)


import threading
from PIL import Image, ImageTk


def compare_screenshots(self):
        def task():
            result, info = compare_last_two_screenshots(self.log_message)
            
            if result is None:
                self.log_message(f"Karşılaştırma başarısız: {info}")
                self.comparison_label.config(text="DINOv2 Karşılaştırma Sonucu: Hata")
                return
                
            file1, file2 = info
            ip1 = file1.split('_')[0]
            ip2 = file2.split('_')[0]
            
            msg = f"DINOv2 Karşılaştırma Sonucu: %{result:.2f}\n({ip1} vs {ip2})"
            self.log_message(msg)
            self.comparison_label.config(text=msg)
            
            # Görüntüleri göster
            for label, file in [(self.image_label1, file1), 
                              (self.image_label2, file2)]:
                try:
                    img = Image.open(file)
                    img.thumbnail((300, 200))
                    photo = ImageTk.PhotoImage(img)
                    label.config(image=photo)
                    label.image = photo
                except Exception as e:
                    self.log_message(f"Görüntü gösterilemedi: {e}")
        
        threading.Thread(target=task, daemon=True).start()
