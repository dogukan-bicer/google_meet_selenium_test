import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image as PILImage, ImageTk
import threading
import os

from quality.image_quality import compare_image_files_dinov2, compare_image_files_dists, compare_image_files_ssim

class ImageComparer:
    def __init__(self, parent):
        self.parent = parent
        self.scrollable_frame = None
        self.base_combo = None

    def open_compare_table_window(self):
        top = tk.Toplevel(self.parent)
        top.title("Resim Karşılaştırma Tablosu")
        top.geometry("1000x600")

        # Seçim UI
        pngs = sorted(
            [f for f in os.listdir('.') if f.endswith('.png')],
            key=os.path.getmtime,
            reverse=True
        )
        if len(pngs) < 2:
            messagebox.showwarning("Uyarı", "En az iki PNG dosyası olmalı!")
            top.destroy()
            return

        sel_frame = ttk.Frame(top)
        sel_frame.pack(fill='x', pady=5, padx=10)
        ttk.Label(sel_frame, text="Karşılaştırılacak baz görüntüyü seçin:").pack(side='left')
        self.base_combo = ttk.Combobox(sel_frame, values=pngs, state='readonly', width=50)
        self.base_combo.current(0)
        self.base_combo.pack(side='left', padx=5)
        ttk.Button(
            sel_frame,
            text="Başlat",
            command=lambda: threading.Thread(
                target=self._build_table,
                args=(top, self.base_combo.get(), pngs),
                daemon=True
            ).start()
        ).pack(side='left', padx=5)

        # Container for table
        container = ttk.Frame(top)
        container.pack(fill="both", expand=True)
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        # Mouse wheel scrolling
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(-1 * (event.delta // 120), "units"))

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_table(self, window, base_img, pngs):
        # Temizle
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Başlık
        headers = ["Baz Görüntü", "Karşılaştırılan", "Dinov2 (%)", "Dists (%)", "SSIM (%)"]
        for col, text in enumerate(headers):
            lbl = ttk.Label(
                self.scrollable_frame,
                text=text,
                width=20,
                anchor="center",
                font=("Arial", 10, "bold"),
                borderwidth=1,
                relief='solid'
            )
            lbl.grid(row=0, column=col, sticky="nsew")

        others = [f for f in pngs if f != base_img]
        for i, other in enumerate(others, start=1):
            vals = [os.path.basename(base_img), os.path.basename(other)]
            try:
                sim1 = compare_image_files_dinov2(base_img, other)
                sim2 = compare_image_files_dists(base_img, other)
                sim3 = compare_image_files_ssim(base_img, other)
                sims = [f"{sim1:.2f}", f"{sim2:.2f}", f"{sim3:.2f}"]
            except Exception as e:
                sims = [f"Hata: {e}"] * 3

            # Populate row
            for col, value in enumerate(vals + sims):
                lbl = ttk.Label(
                    self.scrollable_frame,
                    text=value,
                    width=20,
                    anchor="center",
                    borderwidth=1,
                    relief='solid'
                )
                lbl.grid(row=2*i-1, column=col, sticky="nsew")

            # Show images
            for col, img_path in enumerate([base_img, other]):
                img = PILImage.open(img_path)
                img.thumbnail((150, 100))
                photo = ImageTk.PhotoImage(img)
                lbl_img = ttk.Label(
                    self.scrollable_frame,
                    image=photo,
                    borderwidth=1,
                    relief='solid'
                )
                lbl_img.image = photo
                lbl_img.grid(row=2*i, column=col, padx=5, pady=5, sticky="nsew")

        # Adjust column weights
        for col in range(len(headers)):
            self.scrollable_frame.grid_columnconfigure(col, weight=1)
