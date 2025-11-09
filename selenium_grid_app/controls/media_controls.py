from config.config import driver
import config.config as cfg
import time
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from drivers.remote_driver import get_node_ip_from_grid

# -----------------------------
# Mikrofon ve Kamera Kontrolleri (Ayrı Fonksiyonlar)
# -----------------------------
def toggle_mic(driver, log_func):
    """Doğrudan CTRL+D kısayolunu göndererek mikrofonu toggle eder."""
    driver = cfg.driver
    node_ip = get_node_ip_from_grid(driver, lambda msg: None)
    start = time.time()
    if driver is None:
        log_func("Driver yok, mikrofon kısayolu gönderilemedi.", ip=node_ip)
        return
    try:
        # Odaklamaya çalış (body)
        try:
            driver.execute_script("document.body && document.body.focus && document.body.focus();")
        except Exception:
            pass
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('d').key_up(Keys.CONTROL).perform()
        latency = int((time.time() - start)*1000)
        log_func(f"CTRL+D gönderildi (mikrofon). Gecikme: {latency} ms", ip=node_ip)
    except Exception as e:
        # Alternatif gönderim
        try:
            driver.find_element("tag name", "body").send_keys(Keys.CONTROL, 'd')
            latency = int((time.time() - start)*1000)
            log_func(f"CTRL+D alternatif yöntemle gönderildi. Gecikme: {latency} ms (Önceki hata: {e})", ip=node_ip)
        except Exception as e2:
            latency = int((time.time() - start)*1000)
            log_func(f"Mikrofon kısayolu başarısız: {e2} (İlk hata: {e}) (Gecikme: {latency} ms)", ip=node_ip)

def toggle_cam(driver, log_func):
    """Doğrudan CTRL+E kısayolunu göndererek kamerayı toggle eder."""
    driver = cfg.driver
    node_ip = get_node_ip_from_grid(driver, lambda msg: None)
    start = time.time()
    if driver is None:
        log_func("Driver yok, kamera kısayolu gönderilemedi.", ip=node_ip)
        return
    try:
        try:
            driver.execute_script("document.body && document.body.focus && document.body.focus();")
        except Exception:
            pass
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('e').key_up(Keys.CONTROL).perform()
        latency = int((time.time() - start)*1000)
        log_func(f"CTRL+E gönderildi (kamera). Gecikme: {latency} ms", ip=node_ip)
    except Exception as e:
        try:
            driver.find_element("tag name", "body").send_keys(Keys.CONTROL, 'e')
            latency = int((time.time() - start)*1000)
            log_func(f"CTRL+E alternatif yöntemle gönderildi. Gecikme: {latency} ms (Önceki hata: {e})", ip=node_ip)
        except Exception as e2:
            latency = int((time.time() - start)*1000)
            log_func(f"Kamera kısayolu başarısız: {e2} (İlk hata: {e}) (Gecikme: {latency} ms)", ip=node_ip)

# -----------------------------
# Toggle Fullscreen Fonksiyonu
# -----------------------------
def toggle_fullscreen(log_func):
    driver = cfg.driver  # Global driver'ı kullanıyoruz
    is_fullscreen = cfg.is_fullscreen  # Global değişkeni kullanıyoruz
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
        cfg.is_fullscreen = is_fullscreen  # Global değişkeni güncelle
        latency = int((time.time() - start)*1000)
        log_func(f"Tam ekran togglendi. Gecikme: {latency} ms", ip=node_ip)
    except Exception as e:
        latency = int((time.time() - start)*1000)
        log_func(f"Tam ekran toggle hatası: {e} (Gecikme: {latency} ms)", ip=node_ip)
