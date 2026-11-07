# Selenium Grid settings. Keep local Grid traffic out of any desktop proxy.
import os

_no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
_no_proxy_hosts = {host.strip() for host in _no_proxy.split(",") if host.strip()}
_no_proxy_hosts.update({"localhost", "127.0.0.1"})
os.environ["NO_PROXY"] = ",".join(sorted(_no_proxy_hosts))
os.environ["no_proxy"] = os.environ["NO_PROXY"]

HUB_HOST = "127.0.0.1"
HUB_PORT = "4444"
HUB_URL = f"http://{HUB_HOST}:{HUB_PORT}"
HUB_WD_URL = HUB_URL
HUB_STATUS_URL = f"{HUB_URL}/status"
HUB_CONSOLE_URL = f"{HUB_URL}/grid/console"

# Optional local defaults. Leave credentials out of the repository.
DEFAULT_EMAIL = os.environ.get("GOOGLE_MEET_EMAIL", "")
DEFAULT_PASSWORD = os.environ.get("GOOGLE_MEET_PASSWORD", "")

# Global durum (not: kullanımı dikkatli yap!)
driver = None
is_fullscreen = False

def set_driver(drv):
    global driver

    driver = drv
