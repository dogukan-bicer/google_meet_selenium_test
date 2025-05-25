from utils.grid_utils import get_node_ip_from_grid
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time
import config.config as cfg

# -----------------------------
# Ekran Görüntüsü Alma Fonksiyonu
# -----------------------------
def capture_screenshot(log_func):
    driver = cfg.driver  # Global driver'ı kullanıyoruz
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
        
        
# -----------------------------
# kontrol tuşlarını kapat
# -----------------------------
def press_meeting_buttons_close():
    driver = cfg.driver  # Global driver'ı kullanıyoruz
    
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