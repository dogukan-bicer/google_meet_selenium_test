# Selenium Hub ayarları
HUB_HOST = "localhost"
HUB_PORT = "4444"
HUB_URL = f"http://{HUB_HOST}:{HUB_PORT}"
HUB_WD_URL = f"{HUB_URL}/wd/hub"
HUB_CONSOLE_URL = f"{HUB_URL}/grid/console"
HUB_DIR = r"C:\\Users\\doguk\\Downloads\\selenium-server-3.7.0"
HUB_COMMAND = f"java -jar selenium-server-standalone-3.7.1.jar -role hub -host {HUB_HOST}"

# Varsayılan kullanıcı bilgileri
DEFAULT_EMAIL = "seleniumrtctest@gmail.com"
DEFAULT_PASSWORD = "Test_1234"

# Global durum (not: kullanımı dikkatli yap!)
driver = None
is_fullscreen = False

def set_driver(drv):
    global driver
    driver = drv