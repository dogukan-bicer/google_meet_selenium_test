import os
import time
import requests
from flask import Flask, request, render_template_string, redirect, url_for, jsonify, flash, send_from_directory

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from appwrite.client import Client
from appwrite.services.storage import Storage
from appwrite.input_file import InputFile

import threading
import webbrowser

import pyiqa 
import torch
from PIL import Image
import torchvision.transforms as transforms
# MUSIQ modelini yükle (CPU üzerinde çalıştırmak için; GPU için 'cuda' kullanılabilir)
musiq_model = pyiqa.create_metric('musiq', device='cpu')

# -----------------------------
# Appwrite Ayarları
# -----------------------------

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1')  # Cloud Appwrite endpoint (veya kendi sunucunuzun adresi)
client.set_project('*******')           # Proje ID'niz

# API anahtarını hem client için ayarlıyoruz hem de dosya indirme işlemlerinde kullanmak üzere saklıyoruz.
APPWRITE_API_KEY = '*********'
client.set_key(APPWRITE_API_KEY)

bucket_id_ = "**********"  # Oluşturduğunuz bucket ID'si
storage = Storage(client)

# -----------------------------
# Flask Uygulaması Ayarları
# -----------------------------
app = Flask(__name__)
app.secret_key = "some-secret-flask-key"

# Varsayılan giriş bilgileri
DEFAULT_EMAIL = "*******@gmail.com"
DEFAULT_PASSWORD = "*******"

from appwrite.services.databases import Databases

# Appwrite Database bağlantısını oluştur
databases = Databases(client)

DATABASE_ID = "*********"   # Appwrite Veritabanı ID'si
COLLECTION_ID = "screenshots"           # Ekran görüntülerinin tutulduğu koleksiyon ID'si
bucket_id_screenshots = "******"  # Ekran görüntülerinin yüklendiği bucket ID'si
project_id = "********"               # Appwrite proje ID'si

# -----------------------------
# Selenium (Yerel ChromeDriver) Ayarları
# -----------------------------
driver = None

def setup_driver():
    global driver
    options = Options()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--start-maximized')
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.media_stream_mic": 1,
        "profile.default_content_setting_values.media_stream_camera": 1,
        "profile.default_content_setting_values.geolocation": 0,
        "profile.default_content_setting_values.notifications": 1
    })
    # Eğer headless modda çalıştırmak isterseniz, aşağıdaki satırı açın:
    # options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    return driver

import uuid  # Benzersiz ID oluşturmak için

# Global değişkenler (dosya yükleme işlemlerinde kullanılacak)
folder_counter = 1
current_folder = None

def upload_screenshot_to_appwrite(filename, folder=None):
    """Dosyayı Appwrite Storage’a yükler. Eğer 'folder' belirtilmişse, dosya id'sine klasör adını prefix olarak ekler."""
    try:
        file_obj = InputFile.from_path(filename)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        if folder:
            file_id = f"{folder}__{timestamp}_{uuid.uuid4().hex[:6]}"
        else:
            file_id = f"{timestamp}_{uuid.uuid4().hex[:6]}"
        result = storage.create_file(
            bucket_id=bucket_id_,
            file=file_obj,
            file_id=file_id,
            permissions=['read("any")']
        )
        print("Dosya yüklendi:", result)
        flash("[✓] Ekran görüntüsü Appwrite'a yüklendi!", "success")
    except Exception as e:
        print("Dosya yüklenirken hata:", e)
        flash(f"[!] Dosya yüklenirken hata oluştu: {e}", "error")

def cleanup_old_screenshots():
    """
    Appwrite Storage bucket'ındaki tüm ekran görüntülerini listeler.
    Eğer birden fazla varsa, oluşturulma tarihine göre sıralar ve en son alınanı hariç tüm dosyaları siler.
    """
    try:
        print("Eski ekran görüntüleri temizleme işlemi başlatılıyor...")
        result = storage.list_files(bucket_id_screenshots)
        files = result.get("files", [])
        if len(files) <= 1:
            flash("Silinecek ekran görüntüsü bulunamadı.", "info")
            return
        # "$createdAt" alanına göre sıralama yapıyoruz
        sorted_files = sorted(files, key=lambda x: x.get("$createdAt", ""))
        # En son dosyayı saklayıp geri kalanları siliyoruz
        for file in sorted_files[:-1]:
            file_id = file.get("id") or file.get("$id")
            storage.delete_file(bucket_id_screenshots, file_id)
            print(f"Silindi: {file_id}")
        flash("Bucket içerisindeki eski ekran görüntüleri silindi.", "success")
    except Exception as e:
        flash(f"Silme işlemi sırasında hata: {e}", "error")

# -----------------------------
# Google Hesabı Girişi
# -----------------------------
def login_google(driver, email, password):
    driver.get("https://accounts.google.com/ServiceLogin")
    email_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "identifierId"))
    )
    email_input.send_keys(email)
    driver.find_element(By.ID, "identifierNext").click()
    time.sleep(2)

    password_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "Passwd"))
    )
    password_input.send_keys(password)
    driver.find_element(By.ID, "passwordNext").click()
    time.sleep(5)

# -----------------------------
# Mikrofon ve Kamera Kontrolleri
# -----------------------------
def toggle_mic(driver):
    try:
        elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "VYBDae-Bz112c-RLmnJb"))
        )
        if len(elements) > 1:
            elements[1].click()
        else:
            print("[!] Mikrofon elementi bulunamadı.")
    except Exception as e:
        print("[!] Mikrofon kapatılamadı veya zaten kapalı.", e)

def toggle_cam(driver):
    try:
        elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "VYBDae-Bz112c-RLmnJb"))
        )
        if len(elements) > 3:
            elements[3].click()
        else:
            print("[!] Kamera elementi bulunamadı.")
    except Exception as e:
        print("[!] Kamera kapatılamadı veya zaten kapalı.", e)

# -----------------------------
# Toplantıya Katıl
# -----------------------------
def join_meeting(email, password, meeting_link):
    if not meeting_link:  # Eğer toplantı linki boşsa işlemi durdur
        flash("[!] Toplantı linki bulunamadı. Lütfen geçerli bir link girin!", "error")
        return

    global driver
    driver = setup_driver()
    login_google(driver, email, password)
    driver.get(meeting_link)

    toggle_mic(driver)
    toggle_cam(driver)

    try:
        join_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//span[contains(@class, "UywwFc-RLmnJb")]'))
        )
        driver.execute_script("arguments[0].click();", join_button)
        flash("Toplantıya katılma işlemi başarıyla gerçekleştirildi!", "success")
    except Exception as e:
        flash(f"[!] Katılma butonuna tıklanamadı: {e}", "error")


# -----------------------------
# Yeni Toplantı Oluştur
# -----------------------------
def press_meeting_buttons():
    global driver
    
    try:
        # "Anladım" metnini içeren butonu, içindeki <span> üzerinden hedef alıyoruz.
        anladim_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Anladım']]"))
        )
        # Butonun görünür olduğundan emin olmak için sayfada kaydırıyoruz.
        driver.execute_script("arguments[0].scrollIntoView(true);", anladim_button)
        # Normal click denemesi, başarısız olursa JavaScript click kullanılır.
        try:
            anladim_button.click()
        except Exception:
            driver.execute_script("arguments[0].click();", anladim_button)
        print("Anladım butonuna tıklandı.")
    except Exception as e:
        print("Anladım butonuna tıklanırken hata oluştu:", e)

    try:
        # 'close' ikonuna sahip <i> öğesini bekle ve tıkla
        close_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH, "//i[contains(@class, 'google-material-icons') and normalize-space(text())='close']"
            ))
        )
        driver.execute_script("arguments[0].click();", close_button)
        flash("Close butonuna tıklandı.", "success")
    except Exception as e:
        flash(f"[!] 'Close' butonuna tıklanırken hata: {e}", "error")


def create_meeting(email, password):
    global driver
    driver = setup_driver()
    login_google(driver, email, password)

    # 1) Meet ana sayfasına gidin
    driver.get("https://meet.google.com/landing?pli=1")
    time.sleep(0.1)

    # 2) "Yeni Toplantı" butonunu tıklayın
    start_meeting_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "UywwFc-RLmnJb"))
    )
    driver.execute_script("arguments[0].click();", start_meeting_button)

    # 3) Açılan menünün görünmesi için kısa bekleme
    time.sleep(0.1)

    # 4) "Anlık toplantı başlat" metnini içeren span öğesini bulup tıklayın
    instant_meeting_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[text()='Anlık toplantı başlat']"))
    )
    driver.execute_script("arguments[0].click();", instant_meeting_button)

    press_meeting_buttons()

    flash("Yeni toplantı başarıyla oluşturuldu!", "success")

# -----------------------------
# Tam Ekran
# -----------------------------
# Ekran durumu değişkenini global olarak tanımla
is_fullscreen = False  

def toggle_fullscreen():
    global driver, is_fullscreen  # Global değişkeni kullanacağız
    if driver is None:
        flash("[!] Sürücü henüz başlatılmadı!", "error")
        return

    try:
        if is_fullscreen:
            driver.maximize_window()  # Normal pencere boyutuna geç
        else:
            driver.fullscreen_window()  # Tam ekrana geç
        
        is_fullscreen = not is_fullscreen  # Durumu tersine çevir
        flash("Tam ekran modu değiştirildi.", "success")
    except Exception as e:
        flash(f"[!] Tam ekran modu değiştirilemedi: {e}", "error")

# -----------------------------
# Mikrofon/Kamera Tek Butonda
# -----------------------------
def toggle_mic_cam(action):
    global driver
    if driver is None:
        flash("[!] Sürücü henüz başlatılmadı!", "error")
        return

    if action in ["mic_on", "mic_off"]:
        toggle_mic(driver)
        flash("Mikrofon durumu değiştirildi.", "success")
    elif action in ["cam_on", "cam_off"]:
        toggle_cam(driver)
        flash("Kamera durumu değiştirildi.", "success")

# -----------------------------
# Ekran Görüntüsü Alma ve Appwrite'a Yükleme
# -----------------------------
from datetime import datetime

def capture_element_screenshot(username):
    global driver
    if driver is None:
        driver = setup_driver()
    try:
        # Örneğin bir element bekleniyor (class: "tTdl5d")
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "tTdl5d"))
        )
        screenshot_png = element.screenshot_as_png
        
        # Zaman damgasını saat, dakika, milisaniye (ms) olarak oluşturuyoruz
        timestamp = datetime.now().strftime("%H%M%S%f")[:-3]  # Örneğin: 142530123
        filename = f"{username}_{timestamp}.png"
        with open(filename, "wb") as f:
            f.write(screenshot_png)
        flash(f"[✓] Ekran görüntüsü '{filename}' olarak kaydedildi!", "success")
        
        # Dosyayı Appwrite Storage'a yükle
        upload_screenshot_to_appwrite(filename)
        return filename
    except Exception as e:
        flash(f"[!] Ekran görüntüsü alınamadı: {e}", "error")
        return None



def upload_screenshot_to_appwrite(filename):
    try:
        file_obj = InputFile.from_path(filename)
        result = storage.create_file(
            bucket_id=bucket_id_,
            file=file_obj,
            file_id='unique()',          # Benzersiz dosya ID'si oluşturur
            permissions=['read("any")']   # Dosyanın herkese açık okunmasını sağlar
        )
        print("Dosya yüklendi:", result)
        flash("[✓] Ekran görüntüsü Appwrite'a yüklendi!", "success")
    except Exception as e:
        print("Dosya yüklenirken hata:", e)
        flash(f"[!] Dosya yüklenirken hata oluştu: {e}", "error")

# -----------------------------
# goruntu kalitesi degerlendirme
# -----------------------------

def compute_musiq_score(image_path):
    transform = transforms.Compose([
        transforms.Resize((512, 512)),  # MUSIQ için optimal boyut
        transforms.ToTensor()           # Normalizasyon kaldırıldı, [0,1] aralığı korunuyor
    ])
    image = Image.open(image_path).convert("RGB")
    image_tensor = transform(image).unsqueeze(0)
    with torch.no_grad():
        quality_score = musiq_model(image_tensor).item()
    return quality_score/100  # 0-1 aralığına çevir

from selenium.webdriver.common.action_chains import ActionChains
import time
from selenium.webdriver.common.keys import Keys

def activate_tile_view():
    global driver
    try:

        # Öğeyi bul
# Öğeyi sayfada beklet
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.tTdl5d'))
        )
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()  # Mouse'u üzerine getirir
        flash("Öğenin üzerine gelindi.", "info")
        time.sleep(0.1)
            # 2️⃣ TAB tuşuna bas
# TAB tuşuna birden fazla basma işlemi
        for _ in range(4):  # 4 kez TAB tuşuna basıyoruz
            driver.switch_to.active_element.send_keys(Keys.TAB)
            time.sleep(0.1)  # Her bir TAB tuşu arasında kısa bir bekleme

# Şimdi hangi öğe odaklanmışsa ona tıklayalım
        # Odaklanan öğeyi tıklamak için doğrudan ActionChains kullanma
        time.sleep(0.1)  # Her bir TAB tuşu arasında kısa bir bekleme
        driver.switch_to.active_element.send_keys(Keys.ENTER)
        flash("Öğeye tıklandı.", "info")

        element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//li[@aria-label='Karo içinde göster']"))
        )

# Öğeye tıklama işlemi
        element.click()


        # # JavaScript ile öğeyi seç
        # element = driver.execute_script('return document.querySelector("span.notranslate")')

        # # JavaScript kullanarak öğenin üzerine gelme olayını tetikle
        # driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('mouseover', { bubbles: true }))", element)


        # # 3. "more_vert" ikonunu bekle ve tıkla
        # more_vert_button = WebDriverWait(driver, 10).until(
        #     EC.element_to_be_clickable(
        #         (By.CSS_SELECTOR, 'i.google-material-icons.notranslate.VfPpkd-kBDsod[aria-hidden="true"]')
        #     )
        # )
        # driver.execute_script("arguments[0].click();", more_vert_button)

        # # 4. "Karo içinde göster" butonunu bekle ve tıkla
        # tile_view_button = WebDriverWait(driver, 10).until(
        #     EC.element_to_be_clickable(
        #         (By.CSS_SELECTOR, 'span[jsname="K4r5Ff"].VfPpkd-StrnGf-rymPhb-b9t22c.O6qLGb')
        #     )
        # )
        # driver.execute_script("arguments[0].click();", tile_view_button)

        flash("Karo görünümü etkinleştirildi.", "success")
    except Exception as e:
        flash(f"[!] Karo görünümünü etkinleştirirken hata: {e}", "error")

        print("Karo görünümü etkinleştirilirken hata:", e)




# -----------------------------
# İndirilen ekran görüntülerinin kaydedileceği klasör
# -----------------------------
SCREENSHOTS_FOLDER = os.path.join(app.root_path, 'server_screenshots')
if not os.path.exists(SCREENSHOTS_FOLDER):
    os.makedirs(SCREENSHOTS_FOLDER)

def get_latest_screenshot_url():
    try:
        # Storage içindeki tüm dosyaları listele
        result = storage.list_files(bucket_id_screenshots)

        # Eğer hiç dosya yoksa "Henüz ekran görüntüsü yok" döndür
        files = result.get("files", [])
        if not files:
            return "Henüz ekran görüntüsü yok."

        # En son yüklenen dosyayı bul (createdAt'e göre sıralayarak)
        latest_file = max(files, key=lambda x: x.get("$createdAt", ""))
        file_id = latest_file.get("id") or latest_file.get("$id")
        mode = "admin"  # İstediğiniz mod

        # Appwrite'ın dosya görüntüleme URL formatını kullanarak link oluştur
        remote_url = f"https://cloud.appwrite.io/v1/storage/buckets/{bucket_id_screenshots}/files/{file_id}/view?project={project_id}&mode={mode}"
        print("Remote ekran görüntüsü URL'si:", remote_url)

        # Yetkilendirme header'ları
        headers = {
            "X-Appwrite-Project": project_id,
            "X-Appwrite-Key": APPWRITE_API_KEY
        }

        # Resmi indir
        response = requests.get(remote_url, headers=headers)
        if response.status_code == 200:
            # İçerik türüne göre dosya uzantısını belirleyin (varsayılan .png)
            content_type = response.headers.get('Content-Type')
            ext = '.png'
            if content_type == 'image/jpeg':
                ext = '.jpg'
            elif content_type == 'image/png':
                ext = '.png'
            elif content_type == 'image/gif':
                ext = '.gif'
            
            local_filename = file_id + ext
            local_path = os.path.join(SCREENSHOTS_FOLDER, local_filename)
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            # Kaydedilen dosyaya özel URL oluşturun
            local_url = url_for('serve_screenshot', filename=local_filename)
            print("Local ekran görüntüsü URL'si:", local_url)
            return local_url
        else:
            print("Dosya indirilemedi. Status kodu:", response.status_code)
            return "Dosya indirilemedi."
    except Exception as e:
        print("En son ekran görüntüsü alınırken hata oluştu:", e)
        return "Hata oluştu, ekran görüntüsü alınamadı."

# İndirilen ekran görüntülerini sunmak için özel rota
@app.route('/screenshots/<filename>')
def serve_screenshot(filename):
    return send_from_directory(SCREENSHOTS_FOLDER, filename)

# -----------------------------
# HTML Arayüz (Template)
# -----------------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8" />
    <title>Google Meet Otomasyon</title>
    <style>
        body { font-family: Arial, sans-serif; width: 600px; margin: 30px auto; }
        label { display: block; margin: 10px 0 5px; }
        input[type="text"], input[type="password"] { width: 100%; padding: 8px; }
        button { padding: 10px 20px; margin: 5px 5px 0 0; cursor: pointer; }
        .messages { margin: 10px 0; }
        .success { color: green; }
        .error { color: red; }
        .info { color: blue; }
    </style>
</head>
<body>
    <h1>Google Meet Otomasyon</h1>
    <div class="messages">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for category, msg in messages %}
        <p class="{{ category }}">{{ msg }}</p>
      {% endfor %}
    {% endwith %}
    </div>

    <form method="POST" action="{{ url_for('do_action') }}">
        <label>Kullanıcı Adı (Email):</label>
        <input name="email" type="text" value="{{ default_email }}" />

        <label>Şifre:</label>
        <input name="password" type="password" value="{{ default_password }}" />

        <label>Toplantı Bağlantısı:</label>
        <input name="meeting_link" type="text" />

        <button type="submit" name="action" value="join_meet">Toplantıya Katıl</button>
        <button type="submit" name="action" value="create_meet">Toplantı Oluştur</button>
        <button type="submit" name="action" value="mic_toggle">Mikrofonu Aç/Kapat</button>
        <button type="submit" name="action" value="cam_toggle">Kamerayı Aç/Kapat</button>
        <button type="submit" name="action" value="fullscreen">Tam Ekran</button>
        <button type="submit" name="action" value="capture_element">Görüntü Ögesini Kaydet</button>
        <button type="submit" name="action" value="tile_view">Karo Görünümü</button>
        <br><br>
        <!-- Yeni butonlar -->
        <button type="submit" name="action" value="cleanup_bucket">Sondan Önceki Screenshootları Sil</button>

    </form>
    
    <button type="button" onclick="fetchLatestScreenshot()">En Son Ekran Görüntüsünü Getir</button>
    <h2>En Son Ekran Görüntüsü:</h2>
    {% if screenshot_url and screenshot_url != "Henüz ekran görüntüsü yok." %}
        <img id="screenshot" src="{{ screenshot_url }}" alt="En son ekran görüntüsü" style="max-width:100%; margin-top:20px;">
        {% if screenshot_quality is not none %}
            <p>Görüntü Kalitesi: {{ (screenshot_quality * 100)|round(2) }}%</p>
        {% else %}
            <p>Görüntü kalitesi hesaplanamadı.</p>
        {% endif %}
    {% else %}
        <p>Henüz ekran görüntüsü yok.</p>
    {% endif %}

    <script>
        function fetchLatestScreenshot() {
            fetch("/latest_screenshot")
            .then(response => response.json())
            .then(data => {
                if (data.screenshot_url) {
                    let img = document.getElementById("screenshot");
                    if (!img) {
                        img = document.createElement("img");
                        img.id = "screenshot";
                        img.style.maxWidth = "100%";
                        img.style.marginTop = "20px";
                        document.body.appendChild(img);
                    }
                    img.src = data.screenshot_url;
                    img.style.display = "block";

                    // Dosya adını alıp kalite hesaplaması için ilgili endpoint kullanımı tercih edilebilir.
                    // Veya benzer şekilde kalite bilgisini güncelleyebilirsiniz.
                } else {
                    alert("Ekran görüntüsü bulunamadı!");
                }
            })
            .catch(error => console.error("Hata:", error));
        }
    </script>
</body>
</html>


"""

@app.route("/", methods=["GET"])
def index():
    screenshot_url = get_latest_screenshot_url()  # get_latest_screenshot_url() aynen kalacak
    quality = None

    # Eğer alınan URL hata mesajı değilse, dosya adını alıp yerel dosya yolunu oluşturuyoruz
    if screenshot_url and not screenshot_url.startswith("Hata") and "Henüz ekran görüntüsü yok" not in screenshot_url and "Dosya indirilemedi" not in screenshot_url:
        local_filename = screenshot_url.split('/')[-1]  # '/screenshots/<dosyaadı>' şeklinde
        local_file_path = os.path.join(SCREENSHOTS_FOLDER, local_filename)
        try:
            quality = compute_musiq_score(local_file_path)
        except Exception as e:
            print("Kalite hesaplanırken hata:", e)
            quality = None

    return render_template_string(
        HTML_TEMPLATE,
        default_email=DEFAULT_EMAIL,
        default_password=DEFAULT_PASSWORD,
        screenshot_url=screenshot_url,
        screenshot_quality=quality
    )


@app.route("/latest_screenshot", methods=["GET"])
def latest_screenshot():
    screenshot_url = get_latest_screenshot_url()
    return jsonify({"screenshot_url": screenshot_url})

@app.route("/action", methods=["POST"])
def do_action():
    email = request.form.get("email", DEFAULT_EMAIL)
    password = request.form.get("password", DEFAULT_PASSWORD)
    meeting_link = request.form.get("meeting_link", "")
    action = request.form.get("action", "")

    if action == "join_meet":
        join_meeting(email, password, meeting_link)
    elif action == "create_meet":
        create_meeting(email, password)
    elif action == "mic_toggle":
        toggle_mic_cam("mic_on")
    elif action == "cam_toggle":
        toggle_mic_cam("cam_on")
    elif action == "fullscreen":
        toggle_fullscreen()
    elif action == "capture_element":
        capture_element_screenshot(email)
    elif action == "cleanup_bucket":
        cleanup_old_screenshots()
    elif action == "tile_view":  # Yeni eylem için ekleme yapıyoruz
        activate_tile_view()

    # Kullanıcının girdiği değerleri URL'e ekleyerek yeniden yönlendirin
    return redirect(url_for("index", email=email, password=password))




if __name__ == "__main__":
    port = 5000
    url = f"http://127.0.0.1:{port}"
    # 1 saniyelik gecikme, böylece sunucu başlar başlamaz tarayıcı açılır
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(port=port, debug=True)
