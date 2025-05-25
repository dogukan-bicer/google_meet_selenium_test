import threading
import os
from PIL import Image, ImageTk
from quality.image_quality import compare_image_files_dinov2
from audio.compare_audio import AudioComparer
from tkinter import messagebox

class ScreenshotComparer:
    """
    UI üzerinden son iki ekran görüntüsünü DINOv2 ile karşılaştıran sınıf.
    """
    def __init__(self, parent, comparison_label, image_label1, image_label2, log_func):
        self.parent = parent
        self.comparison_label = comparison_label
        self.image_label1 = image_label1
        self.image_label2 = image_label2
        self.log_func = log_func

    def compare(self):
        """Arayüzden çağrılan ana karşılaştırma metodu."""
        threading.Thread(target=self._task, daemon=True).start()

    def _task(self):
        result, info = self._compare_last_two_screenshots()
        if result is None:
            self.log_func(f"Karşılaştırma başarısız: {info}")
            self.comparison_label.config(text="DINOv2 Karşılaştırma Sonucu: Hata")
            return

        file1, file2 = info
        ip1 = file1.split('_')[0]
        ip2 = file2.split('_')[0]
        msg = f"DINOv2 Karşılaştırma Sonucu: %{result:.2f}\n({ip1} vs {ip2})"
        self.log_func(msg)
        self.comparison_label.config(text=msg)

        for label, file in [(self.image_label1, file1), (self.image_label2, file2)]:
            try:
                img = Image.open(file)
                img.thumbnail((300, 200))
                photo = ImageTk.PhotoImage(img)
                label.config(image=photo)
                label.image = photo
            except Exception as e:
                self.log_func(f"Görüntü gösterilemedi: {e}")

    def _compare_last_two_screenshots(self):
        """
        Son iki .png dosyasını alıp DINOv2 ile karşılaştıran yardımcı metot.
        """
        try:
            pngs = sorted(
                [f for f in os.listdir('.') if f.endswith('.png')],
                key=os.path.getmtime,
                reverse=True
            )[:2]
            if len(pngs) < 2:
                return None, "En az iki PNG gerekli!"

            ip1, ip2 = pngs[0].split('_')[0], pngs[1].split('_')[0]
            if ip1 == ip2:
                return None, "Aynı IP’den karşılaştırılamaz!"

            ret = compare_image_files_dinov2(pngs[0], pngs[1])
            if isinstance(ret, tuple):
                similarity, error = ret
            else:
                similarity, error = ret, None

            if error:
                return None, error
            return similarity, (pngs[0], pngs[1])
        except Exception as e:
            self.log_func(f"DINOv2 hatası: {e}")
            return None, str(e)
