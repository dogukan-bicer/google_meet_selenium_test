from config.config import driver
import config.config as cfg
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from drivers.remote_driver import get_node_ip_from_grid

# -----------------------------
# Mikrofon ve Kamera Kontrolleri (Ayrı Fonksiyonlar)
# -----------------------------
def toggle_mic(driver, log_func):
    driver = cfg.driver  # Global driver'ı kullanıyoruz
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
    driver = cfg.driver  # Global driver'ı kullanıyoruz
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
