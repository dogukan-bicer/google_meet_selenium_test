# image_comparer.py
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image as PILImage, ImageTk

from quality.image_quality import (
    compare_image_files_dinov2_base,
    compare_image_files_dinov2,
    compare_image_files_dists,
    compare_image_files_ssim,
    compare_image_files_openclip
)
from utils.csv_utils import save_results_to_csv
from utils.correlation_utils import compute_correlations_for_pairs

import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

class ImageComparer:
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.ref_folder = None
        self.comp_folder = None
        self.mos_file = None
        self.results = []

    def open_compare_table_window(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Resim Karş. & Korelasyon")
        self.window.geometry("1000x650")

        sel_frame = ttk.Frame(self.window)
        sel_frame.pack(fill='x', padx=10, pady=5)

        # 1) Klasör seçimi
        ttk.Button(sel_frame, text="Referans Klasörü", command=self._select_ref).pack(side='left', padx=5)
        self.lbl_ref = ttk.Label(sel_frame, text="(Seçilmedi)")
        self.lbl_ref.pack(side='left', padx=5)
        ttk.Button(sel_frame, text="Karşıt Klasörü", command=self._select_comp).pack(side='left', padx=5)
        self.lbl_comp = ttk.Label(sel_frame, text="(Seçilmedi)")
        self.lbl_comp.pack(side='left', padx=5)
        self.btn_start = ttk.Button(sel_frame, text="Başlat", state=tk.DISABLED, command=self._on_start)
        self.btn_start.pack(side='left', padx=5)

        # 2) MOS dosyası seçimi
        ttk.Button(sel_frame, text="MOS Dosyası Seç", command=self._select_mos).pack(side='left', padx=5)
        self.lbl_mos = ttk.Label(sel_frame, text="(MOS seçilmedi)")
        self.lbl_mos.pack(side='left', padx=5)

        # 3) CSV butonları
        self.btn_save_csv = ttk.Button(sel_frame, text="CSV Kaydet", state=tk.DISABLED, command=self._on_save_csv)
        self.btn_load_csv = ttk.Button(sel_frame, text="CSV Yükle", command=self._on_load_csv)
        self.btn_corr = ttk.Button(sel_frame, text="Korelasyon Hesapla", state=tk.DISABLED, command=self._on_compute_corr)
        self.btn_save_csv.pack(side='left', padx=5)
        self.btn_load_csv.pack(side='left', padx=5)
        self.btn_corr.pack(side='left', padx=5)

        # Tablo alanı
        container = ttk.Frame(self.window)
        container.pack(fill='both', expand=True)
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)
        self.frame_table = ttk.Frame(canvas)
        canvas.create_window((0,0), window=self.frame_table, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind_all('<MouseWheel>', lambda e: canvas.yview_scroll(-1*(e.delta//120),'units'))
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self._draw_headers()

    def _select_ref(self):
        path = filedialog.askdirectory(title="Referans Klasörü")
        if path:
            self.ref_folder = path
            self.lbl_ref.config(text=os.path.basename(path))
            self._update_start()

    def _select_comp(self):
        path = filedialog.askdirectory(title="Karşıt Klasörü")
        if path:
            self.comp_folder = path
            self.lbl_comp.config(text=os.path.basename(path))
            self._update_start()

    def _select_mos(self):
        path = filedialog.askopenfilename(
            title="MOS Excel Dosyası Seç",
            filetypes=[('Excel','*.xlsx;*.xls')]
        )
        if path:
            self.mos_file = path
            self.lbl_mos.config(text=os.path.basename(path))
            if self.results:
                self.btn_corr.config(state=tk.NORMAL)

    def _update_start(self):
        if self.ref_folder and self.comp_folder:
            self.btn_start.config(state=tk.NORMAL)

    def _draw_headers(self):
        headers = ["Ref","Karşıt","DINOv2-Base (%)","DINOv2-Large (%)","Dists (%)","SSIM (%)","OpenCLIP (%)"]
        for idx, txt in enumerate(headers):
            lbl = ttk.Label(self.frame_table, text=txt, width=15, anchor='center', font=('Arial',10,'bold'), borderwidth=1, relief='solid')
            lbl.grid(row=0, column=idx, sticky='nsew')
            self.frame_table.grid_columnconfigure(idx, weight=1)

    def _on_start(self):
        threading.Thread(target=self._populate_table, daemon=True).start()

    def _populate_table(self):
        for w in self.frame_table.winfo_children(): w.destroy()
        self.results.clear()
        self._draw_headers()

        refs = sorted(f for f in os.listdir(self.ref_folder) if f.lower().endswith(('.png','.jpg','.jpeg','.bmp')))
        comps = sorted(f for f in os.listdir(self.comp_folder) if f.lower().endswith(('.png','.jpg','.jpeg','.bmp')))
        row = 1
        for r in refs:
            prefix = os.path.splitext(r)[0][:2]
            matches = [c for c in comps if c.startswith(prefix) and c != r]
            for c in matches:
                rp, cp = os.path.join(self.ref_folder, r), os.path.join(self.comp_folder, c)
                try:
                    scores = [
                        compare_image_files_dinov2_base(rp, cp),
                        compare_image_files_dinov2(rp, cp),
                        compare_image_files_dists(rp, cp),
                        compare_image_files_ssim(rp, cp),
                        compare_image_files_openclip(rp, cp)
                    ]
                    sims = [f"{s:.2f}" for s in scores]
                except Exception as e:
                    sims = [f"Hata: {e}"]*5

                self.results.append([r, c, *sims])
                for j, path in enumerate((rp,cp)):
                    img = PILImage.open(path); img.thumbnail((100,70))
                    ph = ImageTk.PhotoImage(img)
                    lbl = ttk.Label(self.frame_table, image=ph, borderwidth=1, relief='solid')
                    lbl.image = ph; lbl.grid(row=row, column=j, sticky='nsew')
                for j, val in enumerate([r, c, *sims]):
                    lbl = ttk.Label(self.frame_table, text=val, width=15, anchor='center', borderwidth=1, relief='solid')
                    lbl.grid(row=row+1, column=j, sticky='nsew')
                row += 2

        self.btn_save_csv.config(state=tk.NORMAL)
        if self.mos_file: self.btn_corr.config(state=tk.NORMAL)

    def _on_save_csv(self):
        if not self.results:
            messagebox.showinfo("Boş Sonuç","Kaydedilecek sonuç yok!")
            return
        headers = ["Ref","Karşıt","DINOv2-Base (%)","DINOv2-Large (%)","Dists (%)","SSIM (%)","OpenCLIP (%)"]
        ok, path = save_results_to_csv(self.results, headers)
        if ok: messagebox.showinfo("Kaydedildi", f"Dosya: {path}")
        else: messagebox.showerror("Hata", f"CSV kaydederken hata:\n{path}")

    def _on_load_csv(self):
        path = filedialog.askopenfilename(title="CSV Yükle", filetypes=[('CSV','*.csv')])
        if not path: return
        try:
            df = pd.read_csv(path, sep=';', encoding='utf-8-sig')
            self.results = df.values.tolist()
            # Tabloyu doldur
            for w in self.frame_table.winfo_children(): w.destroy()
            self._draw_headers()
            row = 1
            for r, c, *sims in self.results:
                for j, name in enumerate((r, c)):
                    # sadece metin
                    lbl = ttk.Label(self.frame_table, text=name, width=15, anchor='center', borderwidth=1, relief='solid')
                    lbl.grid(row=row, column=j, sticky='nsew')
                for j, val in enumerate([r, c, *sims]):
                    lbl = ttk.Label(self.frame_table, text=val, width=15, anchor='center', borderwidth=1, relief='solid')
                    lbl.grid(row=row+1, column=j, sticky='nsew')
                row += 2
            if self.mos_file: self.btn_corr.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Hata", f"CSV yüklenirken hata:\n{e}")

    def _on_compute_corr(self):
        if not self.mos_file:
            messagebox.showwarning("MOS Eksik","Önce MOS dosyasını seçin!")
            return

        # Geçici CSV oluştur
        temp_csv = os.path.join(os.getcwd(), "temp_results.csv")
        df_temp = pd.DataFrame(
            self.results,
            columns=["Ref","Karşıt","DINOv2-Base (%)","DINOv2-Large (%)","Dists (%)","SSIM (%)","OpenCLIP (%)"]
        )
        df_temp.to_csv(temp_csv, index=False, sep=';', encoding='utf-8-sig')

        # MOS'lu tablo + özet korelasyon tablosu al
        df_summary, df_with_mos = compute_correlations_for_pairs(
            temp_csv,
            self.mos_file,
            return_merged=True
        )

        # Arayüzde korelasyon özetini göster
        top2 = tk.Toplevel(self.window)
        top2.title("Korelasyon Sonuçları")
        txt = tk.Text(top2, width=60, height=10)
        txt.pack(padx=10, pady=10)
        txt.insert('end', df_summary.to_string(index=False))

        # Excel'e yaz – artık MOS sütunu da ilk sayfada olacak
        wb = Workbook()
        ws1 = wb.active
        ws1.title = "Karşılaştırma"
        for row in dataframe_to_rows(df_with_mos, index=False, header=True):
            ws1.append(row)

        ws2 = wb.create_sheet(title="Korelasyon")
        for row in dataframe_to_rows(df_summary, index=False, header=True):
            ws2.append(row)

        save_path = os.path.join(os.getcwd(), "image_quality_results.xlsx")
        try:
            wb.save(save_path)
            messagebox.showinfo("Kaydedildi", f"Excel oluşturuldu:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"Excel kaydederken hata:\n{e}")

