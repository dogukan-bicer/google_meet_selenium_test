# TC_18 - 

## Test Adımları
	1. Kayıt yetkisi olan bir hesapla toplantı başlat
2. kayit_goruntu.png dosyasını paylaş ve kayit_sesi.wav dosyasını mikrofon kaynağı olarak seç
3. Toplantı kaydını başlat
4. 30 saniye sonra kaydı durdur
5. Kayıt dosyasından görüntü karelerini ve sesi çıkar
6. Görüntü için SSIM, ses için TRILLsson metriklerini hesapla

## Beklenen Sonuç
Kayıt dosyası SSIM ≥ %75 VE TRILLsson ≥ %75

