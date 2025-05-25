from config.config import driver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.grid_utils import get_node_ip_from_grid

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
        log_func(f"Google giriş hatası: " )