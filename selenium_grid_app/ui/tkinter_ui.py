import tkinter as tk
from tkinter import ttk, scrolledtext
from controls.media_controls import toggle_fullscreen, toggle_mic, toggle_cam
from capture.screenshot import capture_screenshot 
from config.config import driver, DEFAULT_EMAIL, DEFAULT_PASSWORD
from utils.logging  import global_log_message
from utils.compare import ScreenshotComparer
from audio.compare_audio import AudioComparer
from ui.compare_windows import CompareWindows
from ui.compare_table import ImageComparer
from utils.hub import HubManager
from audio.recorder import AudioRecorder
import config.config as cfg


# -----------------------------
# Tkinter Arayüzü
# -----------------------------
class SeleniumGridMeetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Selenium Grid Meet Test Arayüzü")
        self.geometry("750x1000")  # Pencere boyutu optimize edildi

        # Scrollable container yapısı
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.content_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        self.content_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Mouse-wheel desteği
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Widget'ları content_frame içine yerleştirme
        self.comparer = ImageComparer(self)
        self.compare_Window = CompareWindows(self)

        # Üst alan: Giriş bilgileri ve node listesi
        top_frame = ttk.Frame(self.content_frame)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        ttk.Label(top_frame, text="Email:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.email_entry = ttk.Entry(top_frame, width=30)
        self.email_entry.insert(0, DEFAULT_EMAIL)
        self.email_entry.grid(row=0, column=1, pady=2)

        ttk.Label(top_frame, text="Şifre:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.password_entry = ttk.Entry(top_frame, width=30, show="*")
        self.password_entry.insert(0, DEFAULT_PASSWORD)
        self.password_entry.grid(row=1, column=1, pady=2)

        ttk.Label(top_frame, text="Toplantı Linki (Varsa):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.meeting_entry = ttk.Entry(top_frame, width=30)
        self.meeting_entry.grid(row=2, column=1, pady=2)

        refresh_btn = ttk.Button(top_frame, text="Node'ları Yenile",command=lambda: self.hub_manager.refresh_nodes(self.node_list))
        refresh_btn.grid(row=0, column=2, padx=5)

        # Node listesi
        self.node_list = tk.Listbox(top_frame, height=5, width=40)
        self.node_list.grid(row=3, column=0, columnspan=3, pady=5)

        # Mevcut karşılaştırma label'ı
        self.TRILLsson_label = ttk.Label(self.content_frame, text="TRILLsson Skoru: N/A")
        self.TRILLsson_label.pack(pady=5)
        
        # Alt alan: Log ekranı
        self.log_text = scrolledtext.ScrolledText(self.content_frame, state="disabled", height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.hub_manager = HubManager(self.log_text)

        # Orta alan: Test butonları
        btn_frame = ttk.Frame(self.content_frame)
        btn_frame.pack(padx=10, pady=5)

        ttk.Button(
            btn_frame, 
            text="Toplantıya Katıl",
            command=lambda: self.hub_manager.join_meeting_test(
                self.email_entry,
                self.password_entry,
                self.meeting_entry,
                self.node_list
            )
        ).grid(row=0, column=0, padx=5, pady=5)

        ttk.Button(
            btn_frame, 
            text="Toplantı Başlat",
            command=lambda: self.hub_manager.create_meeting_test(
                self.email_entry,
                self.password_entry,
                self.node_list
            )
        ).grid(row=0, column=1, padx=5, pady=5)

        ttk.Button(btn_frame, text="Toggle Fullscreen", command=lambda: toggle_fullscreen(self.log_message)).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(btn_frame, text="Toggle Mikrofon", command=lambda: toggle_mic(driver, self.log_message)).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="Toggle Kamera", command=lambda: toggle_cam(driver, self.log_message)).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(btn_frame, text="Ekran Görüntüsü Al", command=lambda: capture_screenshot(self.log_message)).grid(row=2, column=0, padx=5, pady=5)

        ttk.Button(btn_frame, text="Karşılaştırma Tablosu", command=self.comparer.open_compare_table_window).grid(row=3, column=2, padx=5, pady=5)
        
        self.quality_label = ttk.Label(self.content_frame, text="Görüntü Kalitesi: N/A")
        self.quality_label.pack(pady=5)

        self.image_label = ttk.Label(self.content_frame)
        self.image_label.pack(pady=5)

        self.log_message = lambda msg, ip=None: global_log_message(msg, self.log_text, ip)
        
        self.comparison_label = ttk.Label(self.content_frame, text="DINOv2 Karşılaştırma Sonucu: N/A")
        self.comparison_label.pack(pady=5)
        
        self.comparison_frame = ttk.Frame(self.content_frame)
        self.comparison_frame.pack(pady=5)
        
        self.image_label1 = ttk.Label(self.comparison_frame)
        self.image_label1.grid(row=0, column=0, padx=5)
        
        self.image_label2 = ttk.Label(self.comparison_frame)
        self.image_label2.grid(row=0, column=1, padx=5)
        
        self.audio_recorder = AudioRecorder(cfg.driver, self.log_message)
        
        ttk.Button(btn_frame, text="Ses Kaydı Al", 
            command=self.audio_recorder.record_async).grid(row=3, column=1, padx=5, pady=5)
        
        self.screenshot_comparer = ScreenshotComparer(
            parent=self,
            comparison_label=self.comparison_label,
            image_label1=self.image_label1,
            image_label2=self.image_label2,
            log_func=self.log_message
        )
        
        self.audio_comparer = AudioComparer(
            log_func=self.log_message,
            label_widget=self.TRILLsson_label
        )
        
        ttk.Button(btn_frame, text="Sesleri Karşılaştır (TRILLsson)", command=self.audio_comparer.compare).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="Son İki Görüntüyü Karşılaştır", 
                  command=self.screenshot_comparer.compare).grid(row=2, column=2, padx=5, pady=5)
        
        # Menü çubuğu ana pencereye eklendi
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        compare_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Resim Karşılaştırma", menu=compare_menu)
        compare_menu.add_command(label="Karşılaştırma Penceresini Aç", command=self.compare_Window.open_image_compare_window)
        
        audio_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ses Karşılaştırma", menu=audio_menu)
        audio_menu.add_command(label="Penceresini Aç", command=self.compare_Window.open_audio_compare_window)
        
        self.hub_manager.refresh_nodes(self.node_list)