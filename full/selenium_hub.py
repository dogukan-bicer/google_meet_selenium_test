import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import requests
import subprocess
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions  # Yeni ekle
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup  # HTML parse işlemi için
from datetime import datetime  # Ekran görüntüsü için
from urllib.parse import urlparse
import os
import cv2  # OpenCV; ekran görüntüsü alma işlemi için

# Yeni eklenen kısımlar (pyiqa, PIL ve ImageTk ile ilgili)
import pyiqa
from PIL import Image, ImageTk
import torchvision.transforms as transforms
import torch

import base64

from pydub import AudioSegment

# Ayarlar
# HUB_HOST = "localhost"
# HUB_PORT = "4444"
# HUB_URL = f"http://{HUB_HOST}:{HUB_PORT}"
# HUB_WD_URL = f"{HUB_URL}/wd/hub"
# HUB_CONSOLE_URL = f"{HUB_URL}/grid/console"
# HUB_DIR = r"C:\Users\doguk\Downloads\selenium-server-3.7.0"
# HUB_COMMAND = "java -jar selenium-server-standalone-3.7.1.jar -role hub"

HUB_HOST = "localhost"  # Wi-Fi IP'niz
HUB_PORT = "4444"
HUB_URL = f"http://{HUB_HOST}:{HUB_PORT}"
HUB_WD_URL = f"{HUB_URL}/wd/hub"
HUB_CONSOLE_URL = f"{HUB_URL}/grid/console"
HUB_DIR = r"C:\Users\doguk\Downloads\selenium-server-3.7.0"
HUB_COMMAND = f"java -jar selenium-server-standalone-3.7.1.jar -role hub -host {HUB_HOST}"  # Host parametresi eklendi


from pydub import AudioSegment
import numpy as np
# Ayarlar


DEFAULT_EMAIL = "*******"
DEFAULT_PASSWORD = "******"

# Global driver ve fullscreen durumu
driver = None
is_fullscreen = False

# -----------------------------
# Global Log Fonksiyonu
# -----------------------------
# Değiştirilmiş global log fonksiyonu
def global_log_message(text, widget, ip=None):
    """Mesajı konsola ve widget'a IP bilgisi ile yazar."""
    timestamp = time.strftime("%H:%M:%S")
    ip_info = f"[{ip}] " if ip else "[IP Yok] "
    msg = f"{timestamp} - {ip_info}{text}"
    if widget is None:
        print(msg)
    else:
        widget.configure(state="normal")
        widget.insert(tk.END, msg + "\n")
        widget.configure(state="disabled")
        widget.see(tk.END)

# -----------------------------
# Hub İşlemleri
# -----------------------------
def start_hub(log_widget):
    global_log_message("Selenium Hub başlatılıyor...", log_widget)
    try:
        subprocess.Popen(HUB_COMMAND, cwd=HUB_DIR, shell=True)
        time.sleep(5)  # Bekleme süresi kısaltıldı
        global_log_message("Selenium Hub başlatıldı.", log_widget)
    except Exception as e:
        global_log_message(f"Hub başlatılırken hata: {e}", log_widget)

def check_hub_ready():
    status_url = f"{HUB_WD_URL}/status"
    try:
        response = requests.get(status_url, timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def get_connected_nodes():
    """
    Selenium Grid Console sayfasından bağlı node'ları HTML parse yöntemiyle alır.
    Her node için (browser, platform, ip) bilgisi döndürür.
    """
    nodes = []
    try:
        response = requests.get(HUB_CONSOLE_URL, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for proxy in soup.find_all("div", class_="proxy"):
                proxy_text = proxy.get_text()
                
                # Tarayıcı ve platform bilgilerini al
                browser_match = re.search(r"(?:Browser|browserName):\s*(\w+)", proxy_text, re.IGNORECASE)
                browser = browser_match.group(1).strip() if browser_match else "Bilinmiyor"
                
                platform_match = re.search(r"Platform:\s*(\w+)", proxy_text, re.IGNORECASE)
                platform = platform_match.group(1).strip() if platform_match else "Bilinmiyor"
                
                # IP adresini çek (URL'den parse et)
                ip = "Bilinmiyor"
                url_match = re.search(r"http://([\d\.]+):\d+", proxy_text)
                if url_match:
                    ip = url_match.group(1)
                else:
                    # Alternatif olarak proxy ID'sinden IP'yi çıkar
                    proxy_id = proxy.get("id", "")
                    if proxy_id:
                        ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", proxy_id)
                        if ip_match:
                            ip = ip_match.group(1)
                
                nodes.append((browser, platform, ip))
    except Exception as e:
        print(f"Nodes alınırken hata: {e}")
    return nodes

# -----------------------------
# Remote Driver Kurulumu (Chrome için)
# -----------------------------
def remote_setup_driver(browser, platform, log_func):
    """Uzaktan WebDriver kurulumunu yapar."""
    global driver
    if browser.lower() == "chrome":
        options = ChromeOptions()
        options.set_capability("browserName", "chrome")
        options.set_capability("platformName", platform)
        # Grid node kendi binary'sini kullanıyorsa binary_location'a gerek yok.
        
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--disable-notifications")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # WebDriver tespitini engellemek için
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument("--disable-infobars")
        
        # User-Agent ayarı; güncel Chrome sürümüymüş gibi gösterir (örnek: Chrome 135)
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.42 Safari/537.36")
        
        node_ip = get_node_ip_from_grid(driver, lambda msg: None)  # IP'yi sessizce al
        log_func(f"Remote driver kuruluyor: {browser} / {platform}",ip=node_ip)
        try:
            driver = webdriver.Remote(command_executor=HUB_WD_URL, options=options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
        except Exception as e:
            log_func(f"Remote driver kurulamadı: {e}",ip=node_ip)
            return None
    else:
        log_func(f"Hata: {browser} tarayıcısı desteklenmiyor!",ip=node_ip)
        return None

# -----------------------------
# Google Hesabı Girişi
# -----------------------------
def login_google(driver, email, password, log_func):
    try:
        node_ip = get_node_ip_from_grid(driver, lambda msg: None)  # IP'yi sessizce al
        log_func("Google giriş sayfasına gidiliyor...", ip=node_ip)
        driver.get("https://accounts.google.com/ServiceLogin")
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "identifierId"))
        )
        email_input.send_keys(email)
        driver.find_element(By.ID, "identifierNext").click()
        time.sleep(0.1)
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "Passwd"))
        )
        password_input.send_keys(password)
        driver.find_element(By.ID, "passwordNext").click()
        time.sleep(2)  # Girişin tamamlanmasını bekle
        log_func("Google girişi tamamlandı.", ip=node_ip)
    except Exception as e:
        log_func(f"Google giriş hatası: {e}", ip=node_ip)

# -----------------------------
# Mikrofon ve Kamera Kontrolleri (Ayrı Fonksiyonlar)
# -----------------------------
def toggle_mic(driver, log_func):
    node_ip = get_node_ip_from_grid(driver, lambda msg: None)
    start = time.time()
    try:
        elements = WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "VYBDae-Bz112c-RLmnJb"))
        )
        if len(elements) > 1:
            elements[1].click()
            latency = int((time.time() - start)*1000)
            log_func(f"Mikrofon togglendi. Gecikme: {latency} ms", ip=node_ip)
        else:
            latency = int((time.time() - start)*1000)
            log_func(f"Mikrofon elementi bulunamadı. (Gecikme: {latency} ms)", ip=node_ip)
    except Exception as e:
        latency = int((time.time() - start)*1000)
        log_func(f"Mikrofon toggle hatası: {e} (Gecikme: {latency} ms)", ip=node_ip)

def toggle_cam(driver, log_func):
    node_ip = get_node_ip_from_grid(driver, lambda msg: None)
    start = time.time()
    try:
        elements = WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "VYBDae-Bz112c-RLmnJb"))
        )
        if len(elements) > 3:
            elements[3].click()
            latency = int((time.time() - start)*1000)
            log_func(f"Kamera togglendi. Gecikme: {latency} ms", ip=node_ip)
        else:
            latency = int((time.time() - start)*1000)
            log_func(f"Kamera elementi bulunamadı. (Gecikme: {latency} ms)", ip=node_ip)
    except Exception as e:
        latency = int((time.time() - start)*1000)
        log_func(f"Kamera toggle hatası: {e} (Gecikme: {latency} ms)", ip=node_ip)

# -----------------------------
# Toggle Fullscreen Fonksiyonu
# -----------------------------
def toggle_fullscreen(log_func):
    global driver, is_fullscreen
    node_ip = get_node_ip_from_grid(driver, lambda msg: None)
    if driver is None:
        log_func("Sürücü henüz başlatılmadı!", ip=node_ip)
        return
    start = time.time()
    try:
        if is_fullscreen:
            driver.maximize_window()
        else:
            driver.fullscreen_window()
        is_fullscreen = not is_fullscreen
        latency = int((time.time() - start)*1000)
        log_func(f"Tam ekran togglendi. Gecikme: {latency} ms", ip=node_ip)
    except Exception as e:
        latency = int((time.time() - start)*1000)
        log_func(f"Tam ekran toggle hatası: {e} (Gecikme: {latency} ms)", ip=node_ip)

# -----------------------------
# Ekran Görüntüsü Alma Fonksiyonu
# -----------------------------
def capture_screenshot(log_func):
    global driver
    node_ip = get_node_ip_from_grid(driver, log_func)
    if driver is None:
        log_func("Sürücü henüz başlatılmadı!", ip=node_ip)
        return
    start = time.time()
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "tTdl5d"))
        )
        png = element.screenshot_as_png
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]
        filename = f"{node_ip}_{timestamp}.png"
        with open(filename, "wb") as f:
            f.write(png)
        latency = int((time.time() - start)*1000)
        log_func(f"Ekran görüntüsü '{filename}' kaydedildi. Gecikme: {latency} ms", ip=node_ip)
    except Exception as e:
        latency = int((time.time() - start)*1000)
        log_func(f"Ekran görüntüsü alınamadı: {e} (Gecikme: {latency} ms)", ip=node_ip)

def get_node_ip_from_grid(driver, log_func):
    """
    Selenium Grid API üzerinden session_id kullanılarak node IP bilgisini alır.
    Hub API endpoint: /grid/api/testsession?session=<session_id>
    """
    try:
        session_id = driver.session_id
        url = f"{HUB_URL}/grid/api/testsession?session={session_id}"
        log_func(f"Node bilgisi sorgulanıyor: {url}")
        response = requests.get(url, timeout=5)
        data = response.json()
        proxy_id = data.get("proxyId", "")
        if proxy_id:
            parsed = urlparse(proxy_id)
            node_ip = parsed.hostname
            node_ip = node_ip.strip().replace("\\", "")
            log_func(f"Node IP bilgisi alındı: {node_ip}")
            return node_ip
        else:
            log_func("Proxy bilgisi boş; 'unknown' olarak ayarlandı.")
            return "unknown"
    except Exception as e:
        log_func(f"Node IP bilgisi alınamadı: {e}")
        return "unknown"

# -----------------------------
# Toplantıya Katıl
# -----------------------------
def join_meeting(email, password, meeting_link, browser, platform, log_func):
    if not meeting_link:
        log_func("Toplantı linki bulunamadı!", ip="Bilinmiyor")
        return
    
    global driver
    driver = remote_setup_driver(browser, platform, log_func)
    if driver is None:
        return
    
    try:
        node_ip = get_node_ip_from_grid(driver, log_func)
        log_func("Google girişi başlatılıyor...", ip=node_ip)
        login_google(driver, email, password, log_func)
        
        log_func(f"Toplantıya katılım denemesi: {meeting_link}", ip=node_ip)
        driver.get(meeting_link)
        
        # toggle_mic(driver, lambda msg: log_func(msg, ip=node_ip))
        # toggle_cam(driver, lambda msg: log_func(msg, ip=node_ip))
        
        join_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//span[contains(@class, "UywwFc-RLmnJb")]'))
        )
        driver.execute_script("arguments[0].click();", join_button)
        log_func("Toplantıya katılma işlemi tamamlandı.", ip=node_ip)
        
    except Exception as e:
        log_func(f"Toplantıya katılım hatası: {e}", ip=node_ip if 'node_ip' in locals() else "Bilinmiyor")

# -----------------------------
# Yeni Toplantı Oluştur
# -----------------------------
def create_meeting(email, password, browser, platform, log_func):
    global driver
    driver = remote_setup_driver(browser, platform, log_func)
    if driver is None:
        return
    login_google(driver, email, password, log_func)
    driver.get("https://meet.google.com/landing?pli=1")
    time.sleep(0.1)
    try:
        node_ip = get_node_ip_from_grid(driver, lambda msg: None)  # IP'yi sessizce al
        start_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "UywwFc-RLmnJb"))
        )
        driver.execute_script("arguments[0].click();", start_button)
        time.sleep(0.1)
        instant_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Anlık toplantı başlat']"))
        )
        driver.execute_script("arguments[0].click();", instant_button)
        press_meeting_buttons_close()
        log_func("Yeni toplantı başarıyla oluşturuldu.",ip=node_ip)
    except Exception as e:
        log_func(f"Toplantı oluşturma hatası: {e}",ip=node_ip)
        
# -----------------------------
# 3 sn ses kaydı için JS (execute_async_script uyumlu)
# -----------------------------
js_script = """
const callback = arguments[arguments.length - 1];
let chunks = [];
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(stream => {
    const recorder = new MediaRecorder(stream);
    recorder.ondataavailable = e => chunks.push(e.data);
    recorder.onstop = () => {
      stream.getTracks().forEach(t => t.stop());
      const blob = new Blob(chunks, { type: 'audio/webm;codecs=opus' });
      const reader = new FileReader();
      reader.onloadend = () => callback(reader.result.split(',')[1]);
      reader.readAsDataURL(blob);
    };
    recorder.start();
    setTimeout(() => recorder.stop(), 3000);
  })
  .catch(err => callback(new Error('Media error: ' + err.toString())));
"""

def record_audio(log_func, duration=3):
    global driver
    node_ip = get_node_ip_from_grid(driver, log_func)
    start = time.time()
    try:
        driver.set_script_timeout(duration + 5)
        data_b64 = driver.execute_async_script(js_script)
        audio = base64.b64decode(data_b64)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        webm = f"{node_ip}_{ts}.webm"
        mp3  = f"{node_ip}_{ts}.mp3"
        with open(webm, 'wb') as f: f.write(audio)
        subprocess.run(["ffmpeg","-y","-i", webm, mp3], check=True)
        os.remove(webm)
        latency = int((time.time() - start)*1000)
        log_func(f"Ses kaydı tamamlandı: {mp3} (Gecikme: {latency} ms)", ip=node_ip)
        return mp3
    except Exception as e:
        latency = int((time.time() - start)*1000)
        log_func(f"[!] Ses kaydı hatası: {e} (Gecikme: {latency} ms)", ip=node_ip)
        return None
    
# -----------------------------
# Ses Kalitesi Hesaplama (TRILLsson)
# -----------------------------

import librosa
import tensorflow as tf
import tensorflow_hub as hub
from scipy.spatial.distance import cosine

# 1. TRILL modelini bir kez yükle
_trill_model = hub.load("https://tfhub.dev/google/nonsemantic-speech-benchmark/trill/3")

def compare_audio(file1, file2, sample_rate=16000):
    try:
        # 2. Sesleri yükle
        ref, _ = librosa.load(file1, sr=sample_rate, mono=True)
        deg, _ = librosa.load(file2, sr=sample_rate, mono=True)

        # 3. TensorFlow tensörüne dönüştür
        ref_tensor = tf.convert_to_tensor(ref, dtype=tf.float32)[tf.newaxis, :]
        deg_tensor = tf.convert_to_tensor(deg, dtype=tf.float32)[tf.newaxis, :]

        # 4. TRILL embedding çıkar (sample_rate parametresi EKLENDİ)
        ref_embed = _trill_model(samples=ref_tensor, sample_rate=sample_rate)["embedding"]
        deg_embed = _trill_model(samples=deg_tensor, sample_rate=sample_rate)["embedding"]

        # 5. Zaman boyutunda ortalama alarak tek vektöre indir
        ref_vec = tf.reduce_mean(ref_embed, axis=1).numpy().squeeze()
        deg_vec = tf.reduce_mean(deg_embed, axis=1).numpy().squeeze()

        # 6. Kosinüs benzerliği
        similarity = 1 - cosine(ref_vec, deg_vec)
        
        similarity_percent = max(similarity * 100,0)  # normalize et

        return similarity_percent, None
        
    except Exception as e:
        return None, f"TRILL embed hata: {str(e)}"






# -----------------------------
# kontrol tuşlarını kapat
# -----------------------------
def press_meeting_buttons_close():
    global driver
    
    try:
        time.sleep(3)
        # "Anladım" metnini içeren butonu, içindeki <span> üzerinden hedef alıyoruz.
        # Elementi bul ve tıkla
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[jsname='EszDEe']"))
        )
        try:
            element.click()
        except Exception:
            driver.execute_script("arguments[0].click();", element)
        print("Anladım butonuna tıklandı.")
    except Exception as e:
        print("[!] Anladım butonuna tıklanırken hata oluştu:", e)
    time.sleep(1)
    try:
        # 'close' ikonuna sahip <i> öğesini bekle ve tıkla
        close_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH, "//i[contains(@class, 'google-material-icons') and normalize-space(text())='close']"
            ))
        )
        driver.execute_script("arguments[0].click();", close_button)
        print("Close butonuna tıklandı.", "success")
    except Exception as e:
        print(f"[!] 'Close' butonuna tıklanırken hata: {e}", "error")

# -----------------------------
# Ekran Görüntüsü Kalitesi Hesaplama (BRISQUE)
# -----------------------------
# Global BRISQUE modeli oluşturuluyor (CPU üzerinden çalışacak şekilde)
brisque_model = pyiqa.create_metric('brisque', device='cpu')

def brisque_to_percentage(brisque_score, min_val=0, max_val=100):
    """
    BRISQUE skorunu 0-100 aralığına normalize edip yüzde olarak döndürür.
    min_val: En iyi kalite için skor (genellikle 0)
    max_val: En kötü kalite için skor (örneğin 100)
    """
    score = max(min(brisque_score, max_val), min_val)
    return (1 - (score - min_val) / (max_val - min_val)) * 100

def calculate_screenshot_quality():
    """
    Çalışma dizinindeki en son kaydedilmiş .png dosyasını bulur, PIL ile açar,
    torchvision transformları ile modele uygun formata getirir ve 
    pyiqa kütüphanesi aracılığıyla BRISQUE skoru hesaplayıp yüzdeye çevirir.
    """
    png_files = [f for f in os.listdir('.') if f.endswith('.png')]
    if not png_files:
        return None, "Ekran görüntüsü bulunamadı."
    latest_file = max(png_files, key=os.path.getmtime)
    
    try:
        image = Image.open(latest_file).convert("RGB")
    except Exception as e:
        return None, f"Resim açılırken hata: {e}"
    
    transform = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.ToTensor(),
    ])
    image_tensor = transform(image).unsqueeze(0)
    
    try:
        quality_score = brisque_model(image_tensor).item()
        percentage_score = brisque_to_percentage(quality_score)
        return percentage_score, latest_file
    except Exception as e:
        return None, f"Kalite hesaplanırken hata: {e}"
    


# -----------------------------
# Tkinter Arayüzü
# -----------------------------
class SeleniumGridMeetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Selenium Grid Meet Test Arayüzü")
        # Ana pencere boyutunu güncelleyin
        self.geometry("750x1000")

        # Mevcut karşılaştırma label'ının altına TRILLsson label'ını ekleyin
        self.TRILLsson_label = ttk.Label(self, text="TRILLsson Skoru: N/A")
        self.TRILLsson_label.pack(pady=5)
        
        # Üst alan: Giriş bilgileri ve node listesi
        top_frame = ttk.Frame(self)
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

        refresh_btn = ttk.Button(top_frame, text="Node'ları Yenile", command=self.refresh_nodes)
        refresh_btn.grid(row=0, column=2, padx=5)

        # Node listesi
        self.node_list = tk.Listbox(top_frame, height=5, width=40)
        self.node_list.grid(row=3, column=0, columnspan=3, pady=5)

        # Orta alan: Test butonları
        btn_frame = ttk.Frame(self)
        btn_frame.pack(padx=10, pady=5)
        ttk.Button(btn_frame, text="Toplantıya Katıl", command=self.join_meeting_test).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(btn_frame, text="Toplantı Başlat", command=self.create_meeting_test).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="Toggle Fullscreen", command=lambda: toggle_fullscreen(self.log_message)).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(btn_frame, text="Toggle Mikrofon", command=lambda: toggle_mic(driver, self.log_message)).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="Toggle Kamera", command=lambda: toggle_cam(driver, self.log_message)).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(btn_frame, text="Ekran Görüntüsü Al", command=lambda: capture_screenshot(self.log_message)).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(btn_frame, text="Görüntü Kalitesini Hesapla", command=self.calculate_quality_test).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="Son İki Görüntüyü Karşılaştır", 
                  command=self.compare_screenshots).grid(row=2, column=2, padx=5, pady=5)
        ttk.Button(btn_frame, text="Ses Kaydı Al", command=self.record_audio).grid(row=3, column=0, padx=5, pady=5)
        ttk.Button(btn_frame, text="Sesleri Karşılaştır (TRILLsson)", command=self.compare_audio).grid(row=3, column=1, padx=5, pady=5)
        
        # Karşılaştırma sonuçları için yeni label
        self.comparison_label = ttk.Label(self, text="DINOv2 Karşılaştırma Sonucu: N/A")
        self.comparison_label.pack(pady=5)
        
        # Karşılaştırma görüntüleri için frame
        self.comparison_frame = ttk.Frame(self)
        self.comparison_frame.pack(pady=5)
        
        self.image_label1 = ttk.Label(self.comparison_frame)
        self.image_label1.grid(row=0, column=0, padx=5)
        
        self.image_label2 = ttk.Label(self.comparison_frame)
        self.image_label2.grid(row=0, column=1, padx=5)
        
        # Yeni label için
        self.TRILLsson_label = ttk.Label(self, text="TRILLsson Skoru: N/A")
        self.TRILLsson_label.pack(pady=5)

        # Alt alan: Log ekranı
        self.log_text = scrolledtext.ScrolledText(self, state="disabled", height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Kalite sonucu için bir label ekleyelim:
        self.quality_label = ttk.Label(self, text="Görüntü Kalitesi: N/A")
        self.quality_label.pack(pady=5)

        # Görüntüyü göstermek için yeni bir Label ekliyoruz.
        self.image_label = ttk.Label(self)
        self.image_label.pack(pady=5)

        # Global log mesajı fonksiyonunu, log ekranına yazacak şekilde atıyoruz.
        self.log_message = lambda msg, ip=None: global_log_message(msg, self.log_text, ip)

        self.refresh_nodes()
        
    

    def refresh_nodes(self):
        self.node_list.delete(0, tk.END)
        self.log_message("Node'lar sorgulanıyor...")
        nodes = get_connected_nodes()
        if nodes:
            for browser, platform, ip in nodes:
                self.node_list.insert(tk.END, f"{browser} - {platform} - {ip}")
            self.log_message(f"{len(nodes)} node bulundu.")
        else:
            self.log_message("Hiçbir node bulunamadı veya hata oluştu.")
            
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
        

    def get_selected_node(self):
        selection = self.node_list.curselection()
        if not selection:
            messagebox.showwarning("Uyarı", "Lütfen test için bir node seçin!")
            return None, None
        selected_text = self.node_list.get(selection[0])
        try:
            parts = selected_text.split("-")
            if len(parts) < 2:
                raise ValueError("Eksik node bilgisi")
            return parts[0].strip(), parts[1].strip()
        except Exception as e:
            messagebox.showerror("Hata", f"Node bilgileri okunamadı: {e}")
            return None, None

    def join_meeting_test(self):
        browser, platform = self.get_selected_node()
        if browser is None:
            return
        email = self.email_entry.get()
        password = self.password_entry.get()
        meeting_link = self.meeting_entry.get()
        threading.Thread(
            target=join_meeting, 
            args=(email, password, meeting_link, browser, platform, self.log_message),
            daemon=True
        ).start()

    def create_meeting_test(self):
        browser, platform = self.get_selected_node()
        if browser is None:
            return
        email = self.email_entry.get()
        password = self.password_entry.get()
        threading.Thread(
            target=create_meeting, 
            args=(email, password, browser, platform, self.log_message),
            daemon=True
        ).start()
        
    def record_audio(self):
        def task():
            filename = record_audio(self.log_message)
            if filename:
                self.log_message(f"Ses kaydı tamamlandı: {filename}")
        threading.Thread(target=task, daemon=True).start()

    def compare_audio(self):
        def task():
            audio_files = sorted([f for f in os.listdir('.') if f.endswith('.mp3')], 
                            key=os.path.getmtime, 
                            reverse=True)[:2]
            if len(audio_files) < 2:
                self.log_message("Karşılaştırma için en az iki ses kaydı gerekli!")
                return
            
            file1, file2 = audio_files
            self.log_message(f"Karşılaştırılan dosyalar: {file1}, {file2}")
            score, error = compare_audio(file1, file2)
        
            if score is not None:
                ip1 = file1.split('_')[0]
                ip2 = file2.split('_')[0]
                msg = f"TRILLsson Skoru ({ip1} vs {ip2}): {score:.2f}"
                self.TRILLsson_label.config(text=msg)
                self.log_message(msg)
            else:
                self.log_message(f"Hata: {error}")
        threading.Thread(target=task, daemon=True).start()
    
        
# -----------------------------
# Görüntü kalitesi testi
# -----------------------------

    def calculate_quality_test(self):
        def task():
            quality, info = calculate_screenshot_quality()
            if quality is None:
                self.log_message(f"Kalite hesaplanamadı: {info}", ip="Bilinmiyor")
                self.quality_label.config(text="Görüntü Kalitesi: Hata")
            else:
                try:
                    node_ip = info.split("_")[0]
                except Exception:
                    node_ip = "Unknown"
                msg = f"{info} dosyası üzerinden {node_ip} IP'sine ait görüntü kalitesi hesaplandı: %{quality:.2f}"
                self.log_message(msg)
                self.quality_label.config(text=f"Görüntü Kalitesi: %{quality:.2f} ({node_ip} IP)")
                
                # Hesaplanan görüntüyü PIL ile aç ve Tkinter'da göster.
                try:
                    img = Image.open(info)
                    # Görüntünün boyutunu ayarlayarak küçültüyoruz (örneğin 400x300)
                    img.thumbnail((400, 300))
                    photo = ImageTk.PhotoImage(img)
                    self.image_label.config(image=photo)
                    self.image_label.image = photo  # Referansı saklamak önemli
                except Exception as e:
                    self.log_message(f"Hata: {e}", ip="Bilinmiyor")
        threading.Thread(target=task, daemon=True).start()

import os
import torch
import torch.nn.functional as F
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

# Cihaz ayarı
_device = "cuda" if torch.cuda.is_available() else "cpu"

# DINOv2 model ve işlemcisi (BASE sürüm)
_processor = AutoImageProcessor.from_pretrained('facebook/dinov2-large')
_model = AutoModel.from_pretrained('facebook/dinov2-large').to(_device)

def compare_last_two_screenshots(log_func):
    """
    DINOv2 (facebook/dinov2-large) kullanarak son iki ekran görüntüsünü karşılaştırır.
    CLS token'dan çıkarılan özelliklerle kosinüs benzerliği döner.
    """
    try:
        # Son 2 PNG dosyasını bul
        png_files = sorted(
            [f for f in os.listdir('.') if f.endswith('.png')],
            key=os.path.getmtime,
            reverse=True
        )[:2]

        if len(png_files) < 2:
            return None, "Karşılaştırma için en az iki ekran görüntüsü gerekli!"
        
        ip1 = png_files[0].split('_')[0]
        ip2 = png_files[1].split('_')[0]
        if ip1 == ip2:
            return None, "Aynı IP'den ekran görüntüleri karşılaştırılamaz!"

        # Görüntüleri yükle ve yeniden boyutlandır
        img1 = Image.open(png_files[0]).convert('RGB').resize((600, 600))
        img2 = Image.open(png_files[1]).convert('RGB').resize((600, 600))

        # Görüntüleri işleme ve modele ver
        inputs = _processor(images=[img1, img2], return_tensors="pt").to(_device)

        with torch.no_grad():
            outputs = _model(**inputs)
            features = outputs.last_hidden_state[:, 0, :]  # CLS token kullanımı

        # Kosinüs benzerliği hesapla
        similarity = F.cosine_similarity(features[0], features[1], dim=0).item()
        similarity_percent = max(similarity * 100,0)  # normalize et

        return similarity_percent, (png_files[0], png_files[1])

    except Exception as e:
        log_func(f"DINOv2 ile karşılaştırma hatası: {e}")
        return None, f"Karşılaştırma hatası: {e}"

def main():
    if not check_hub_ready():
        print("Hub çalışmıyor, başlatılıyor...")
        start_hub(log_widget=None)
        for i in range(1, 11):
            if check_hub_ready():
                print("Hub başarıyla başlatıldı!")
                break
            print(f"Bekleniyor... ({i}/10)")
            time.sleep(0.1)
        else:
            messagebox.showerror("Hata", "Hub başlatılamadı! Uygulama kapatılıyor.")
            return

    app = SeleniumGridMeetApp()
    app.mainloop()

if __name__ == "__main__":
    main()
