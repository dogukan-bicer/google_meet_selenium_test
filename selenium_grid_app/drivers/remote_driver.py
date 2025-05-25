from config.config import driver, HUB_WD_URL, HUB_URL
import config.config as cfg
from selenium import webdriver
import requests
from urllib.parse import urlparse
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from capture.screenshot import press_meeting_buttons_close
from auth.google_auth import login_google
from utils.grid_utils import get_node_ip_from_grid
from config.config import set_driver

# -----------------------------
# Remote Driver Kurulumu (Chrome için)
# -----------------------------

def remote_setup_driver(browser, platform, log_func):
    """Uzaktan WebDriver kurulumunu yapar."""
    driver = cfg.driver  # Global driver'ı kullanıyoruz
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
        
        print(f"..Remote driver kurulumu başlatılıyor: {browser} / {platform}")
        print("/////driver:", driver)
        node_ip = get_node_ip_from_grid(driver, None)  # IP'yi sessizce al
        try:
            driver = webdriver.Remote(command_executor=HUB_WD_URL, options=options)
            log_func(f"Remote driver kuruluyor: {browser} / {platform}",ip=node_ip)
            print(f"****Remote driver başarıyla kuruldu: {browser} / {platform} (IP: {node_ip})")
            print("*****driver:", driver)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            set_driver(driver)
            return driver
        except Exception as e:
            log_func(f"Remote driver kurulamadı: {e}",ip=node_ip)
            return None
    else:
        log_func(f"Hata: {browser} tarayıcısı desteklenmiyor!",ip=node_ip)
        return None

# -----------------------------
# Yeni Toplantı Oluştur
# -----------------------------
def create_meeting(email, password, browser, platform, log_func):
    driver = cfg.driver  # Global driver'ı kullanıyoruz
    print(f"create_meeting fonksiyonu çağrıldı: {email}, {password}, {browser}, {platform}")
    print(f"Global driver: {driver}")
    driver = remote_setup_driver(browser, platform, log_func)
    cfg.driver = driver  # Global driver'ı güncelle
    print(f"************Remote driver kuruldu: {driver}")
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
# Toplantıya Katıl
# -----------------------------
def join_meeting(email, password, meeting_link, browser, platform, log_func):
    if not meeting_link:
        log_func("Toplantı linki bulunamadı!", ip="Bilinmiyor")
        return
    
    driver = cfg.driver  # Global driver'ı kullanıyoruz
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
        cfg.driver = driver  # Global driver'ı güncelle
        log_func("Toplantıya katılma işlemi tamamlandı.", ip=node_ip)
        
    except Exception as e:
        log_func(f"Toplantıya katılım hatası: {e}", ip=node_ip if 'node_ip' in locals() else "Bilinmiyor")