# TC_11 - 

## Test Adımları
1. Bir toplantıya katıl
2. Ekran paylaşımı başlat ve test_goruntusu.png dosyasını paylaş
3. Alıcı tarafta ekran görüntüsü al
4. Alınan görüntü için SSIM, DINOv2 base ve OpenCLIP metriklerini ayrı ayrı hesapla
5. Tüm metriklerin eşik değerlerini sağladığını doğrula

## Beklenen Sonuç
SSIM ≥ %75 VE DINOv2 ≥ %70 VE OpenCLIP ≥ %65

