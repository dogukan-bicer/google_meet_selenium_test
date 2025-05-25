import tkinter as tk
from tkinter import ttk, messagebox
import os
from quality.image_quality import compare_image_files_dinov2, compare_image_files_dists, compare_image_files_ssim
import threading
from PIL import Image as PILImage, ImageTk
from audio.compare_audio import AudioComparer
from PIL import Image, ImageTk

class CompareWindows:
    def __init__(self, parent):
        self.parent = parent
        self.compare_listbox = None
        self.audio_listbox = None
        self.image_score_label = None
        self.audio_score_label = None
        self.image_files_frame = None
        self.audio_files_frame = None

    def open_image_compare_window(self):
        """Yeni Toplevel pencerede en son PNG’leri listeler ve karşılaştırma yapar."""
        top = tk.Toplevel(self.parent)
        top.title("Resim Karşılaştırma")
        top.geometry("500x400")

        ttk.Label(top, text="Karşılaştırmak için iki farklı IP’ye ait resmi seçin:").pack(pady=5)

        # En son 10 PNG dosyasını alıp, yanında IP’siyle listbox’a ekliyoruz
        pngs = sorted(
            [f for f in os.listdir('.') if f.endswith('.png')],
            key=os.path.getmtime,
            reverse=True
        )[:100]
        display_items = [f"{fn}    ({fn.split('_')[0]})" for fn in pngs]

        # Frame içine Listbox ve Scrollbar ekle
        list_frame = ttk.Frame(top)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.compare_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.MULTIPLE,
            yscrollcommand=scrollbar.set,
            width=60,
            height=10
        )
        scrollbar.config(command=self.compare_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.compare_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for item in display_items:
            self.compare_listbox.insert(tk.END, item)

        ttk.Button(top, text="Karşılaştır", command=lambda: self.do_compare(top, pngs)).pack(pady=5)

    def do_compare(self, window, pngs):
        sel = self.compare_listbox.curselection()
        if len(sel) != 2:
            messagebox.showwarning("Uyarı", "Lütfen tam olarak iki resim seçin.")
            return

        file1, file2 = pngs[sel[0]], pngs[sel[1]]
        ip1, ip2 = file1.split('_')[0], file2.split('_')[0]
        if ip1 == ip2:
            messagebox.showerror("Hata", "Aynı IP'den iki resim seçilemez.")
            return

        # Burada dönüşün tuple olduğunu varsayıp unpack ediyoruz:
        similarity = compare_image_files_dinov2(file1, file2)

        # Kendi sonuç penceremizi oluşturuyoruz:
        result = tk.Toplevel(self.parent)
        result.title("Benzerlik Sonucu")
        result.geometry("700x500")

        text = f"{file1} ({ip1})  vs  {file2} ({ip2})\nBenzerlik: %{similarity:.2f}"
        ttk.Label(result, text=text, font=("Arial", 12, "bold")).pack(pady=10)

        # Resimleri yan yana göster
        img_frame = ttk.Frame(result)
        img_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        for path in (file1, file2):
            try:
                img = Image.open(path)
                img.thumbnail((320, 320))
                photo = ImageTk.PhotoImage(img)
                lbl = ttk.Label(img_frame, image=photo)
                lbl.image = photo
                lbl.pack(side=tk.LEFT, padx=10)
            except Exception as e:
                ttk.Label(img_frame, text=f"Resim yüklenemedi:\n{e}").pack(side=tk.LEFT, padx=10)

        ttk.Button(result, text="Kapat", command=result.destroy).pack(pady=10)
        window.destroy()


    def open_audio_compare_window(self):
        top = tk.Toplevel(self.parent)
        top.title("Ses Karşılaştırma")
        top.geometry("400x400")
        ttk.Label(top, text="Karşılaştırmak için iki ses dosyası seçin:").pack(pady=5)

        audios = sorted(
            [f for f in os.listdir('.') if f.endswith('.mp3')],
            key=os.path.getmtime,
            reverse=True
        )[:10]
        display = audios

        self.audio_listbox = tk.Listbox(
            top,
            selectmode=tk.MULTIPLE,
            width=50,
            height=10
        )
        for item in display:
            self.audio_listbox.insert(tk.END, item)
        self.audio_listbox.pack(pady=5)

        ttk.Button(
            top,
            text="Karşılaştır",
            command=lambda: self.do_compare_audio(top, audios)
        ).pack(pady=5)

    def do_compare_audio(self, window, files):
        sel = self.audio_listbox.curselection()
        if len(sel) != 2:
            messagebox.showwarning("Uyarı", "Lütfen tam olarak iki ses dosyası seçin.")
            return
        f1, f2 = files[sel[0]], files[sel[1]]

        score, error = AudioComparer.compare_audio_files(f1, f2)
        if error:
            messagebox.showerror("Hata", error)
            return

        if self.audio_score_label:
            self.audio_score_label.destroy()
        self.audio_score_label = ttk.Label(
            window,
            text=f"Benzerlik: %{score:.2f}",
            font=(None, 12, "bold")
        )
        self.audio_score_label.pack(pady=10)

        if self.audio_files_frame:
            self.audio_files_frame.destroy()
        self.audio_files_frame = ttk.Frame(window)
        self.audio_files_frame.pack(pady=5)
        ttk.Label(self.audio_files_frame, text=f1).pack(side=tk.LEFT, padx=10)
        ttk.Label(self.audio_files_frame, text=f2).pack(side=tk.LEFT, padx=10)
