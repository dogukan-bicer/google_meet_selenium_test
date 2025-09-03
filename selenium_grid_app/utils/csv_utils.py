# csv_utils.py
import csv
import os
from tkinter import filedialog, messagebox


def save_results_to_csv(results, headers, default_filename="results.csv"):
    """
    CSV dosyasına kaydetme fonksiyonu (Excel uyumlu, hücre bazlı açılır).

    :param results: List[List[str]]  - CSV’ye yazılacak satırlar
    :param headers: List[str]        - CSV başlıkları
    :param default_filename: str     - Önerilen dosya adı
    :return: (bool, str)             - (Başarılı mı?, Dosya yolu veya hata mesajı)
    """
    # Kaydetme diyalogunu aç
    save_path = filedialog.asksaveasfilename(
        defaultextension='.csv',
        filetypes=[('CSV files', '*.csv')],
        initialfile=default_filename,
        title='Sonuçları CSV olarak kaydet'
    )
    if not save_path:
        return False, "Kayıt iptal edildi"

    try:
        # Hedef klasörü oluştur (varsa atla)
        directory = os.path.dirname(save_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        # Excel'in hücreleri ayırması için noktalı virgül delimiter kullan, UTF-8 BOM ile kaydet
        with open(save_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            # Başlık satırı
            writer.writerow(headers)
            # Veri satırları
            writer.writerows(results)

        return True, save_path

    except Exception as e:
        return False, str(e)