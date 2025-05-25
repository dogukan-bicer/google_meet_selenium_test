# utils/grid_utils.py

import requests
from urllib.parse import urlparse
from config.config import HUB_URL

def get_node_ip_from_grid(driver, log_func):
    """
    Selenium Grid API üzerinden session_id kullanılarak node IP bilgisini alır.
    """
    if driver is None:
        if log_func:
            log_func("Driver örneği None, node IP alınamıyor!")
        return "unknown"

    try:
        session_id = driver.session_id
        url = f"{HUB_URL}/grid/api/testsession?session={session_id}"
        if log_func:
            log_func(f"Node bilgisi sorgulanıyor: {url}")
        response = requests.get(url, timeout=5)
        data = response.json()
        proxy_id = data.get("proxyId", "")
        if proxy_id:
            parsed = urlparse(proxy_id)
            node_ip = parsed.hostname
            node_ip = node_ip.strip().replace("\\", "")
            if log_func:
                log_func(f"Node IP bilgisi alındı: {node_ip}")
            return node_ip
        else:
            if log_func:
                log_func("Proxy bilgisi boş; 'unknown' olarak ayarlandı.")
            return "unknown"
    except Exception as e:
        if log_func:
            log_func(f"Node IP bilgisi alınamadı: {e}")
        return "unknown"


