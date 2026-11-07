import os
import re
import threading
import subprocess
import requests
import tkinter as tk
from tkinter import messagebox
from bs4 import BeautifulSoup
from utils.logging import global_log_message
from config.config import HUB_WD_URL, HUB_STATUS_URL, HUB_CONSOLE_URL
from pathlib import Path
import json
from drivers.remote_driver import join_meeting, create_meeting


def _get_local(url, timeout=3):
    session = requests.Session()
    session.trust_env = False
    return session.get(url, timeout=timeout)

class HubManager:
    def __init__(self, log_widget=None):
        self.log_widget = log_widget

    def log(self, message, ip=None):
        """
        Mesajı console ve log_widget'a yazar; ip isteğe bağlı.
        """
        if self.log_widget:
            global_log_message(message, self.log_widget, ip)
        else:
            prefix = f"[{ip}] " if ip else ""
            print(f"{prefix}{message}")

    def start_hub(self):
        """Start a local Selenium Grid 4 standalone server with the local Brave browser."""
        if self.check_hub_ready():
            self.log("Selenium Grid zaten çalışıyor.")
            return
        self.log("Yerel Selenium Grid ve Brave node'u başlatılıyor...")
        try:
            from selenium.webdriver.common.selenium_manager import SeleniumManager

            version = "4.52.0"
            jar = Path.home() / ".cache" / "selenium" / "grid" / version / f"selenium-server-{version}.jar"
            if not jar.is_file():
                subprocess.run(
                    [str(SeleniumManager._get_binary()), "--grid", version, "--avoid-stats"],
                    check=True,
                    timeout=300,
                    env=os.environ.copy(),
                )
            if not jar.is_file():
                raise FileNotFoundError(f"Selenium Server jar bulunamadı: {jar}")

            brave = Path("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")
            chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
            browser = brave if brave.is_file() else chrome
            if not browser.is_file():
                raise FileNotFoundError("Brave Browser veya Google Chrome /Applications altında bulunamadı.")

            stereotype = {
                "browserName": "chrome",
                "platformName": "MAC",
                "goog:chromeOptions": {"binary": str(browser)},
            }
            config_path = Path.home() / ".cache" / "selenium" / "local-grid.toml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                "[node]\n"
                "detect-drivers = false\n"
                "max-sessions = 1\n\n"
                "[[node.driver-configuration]]\n"
                f"display-name = {json.dumps(browser.parent.parent.parent.stem)}\n"
                "max-sessions = 1\n"
                f"stereotype = {json.dumps(json.dumps(stereotype))}\n",
                encoding="utf-8",
            )

            log_path = Path.home() / "Library" / "Logs" / "selenium-meet-grid.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_file = log_path.open("a", encoding="utf-8")
            env = os.environ.copy()
            env["NO_PROXY"] = env["no_proxy"] = "localhost,127.0.0.1"
            command = [
                "java", "-jar", str(jar), "standalone", "--host", "127.0.0.1",
                "--config", str(config_path), "--selenium-manager", "true",
            ]
            grid_process = subprocess.Popen(
                command,
                cwd=str(config_path.parent),
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            log_file.close()
            (config_path.parent / "local-grid.pid").write_text(str(grid_process.pid), encoding="ascii")
            self.log(f"Yerel Grid başlatılıyor. Tarayıcı node'u: {browser.parent.parent.parent.stem}")
        except Exception as e:
            self.log(f"Yerel Selenium Grid başlatılamadı: {e}")

    def check_hub_ready(self):
        try:
            response = _get_local(HUB_STATUS_URL)
            return response.status_code == 200
        except Exception:
            return False

    def get_selected_node(self, node_listbox):
        """
        Listbox'tan seçili node'u alır, 'browser - platform - ip' formatında ayrıştırır.
        Seçim yoksa uyarı gösterir ve (None, None) döner.
        """
        sel = node_listbox.curselection()
        if not sel:
            messagebox.showwarning("Uyarı", "Lütfen test için bir node seçin!")
            return None, None
        try:
            text = node_listbox.get(sel[0])
            parts = [p.strip() for p in text.split(" - ")]
            if len(parts) < 2:
                raise ValueError("Eksik node bilgisi")
            browser, platform = parts[0], parts[1]
            return browser, platform
        except Exception as e:
            messagebox.showerror("Hata", f"Node bilgileri okunamadı: {e}")
            return None, None

    def join_meeting_test(self, email_entry, password_entry, meeting_entry, node_listbox):
        browser, platform = self.get_selected_node(node_listbox)
        if browser is None:
            return
        email = email_entry.get()
        password = password_entry.get()
        meeting_link = meeting_entry.get()
        threading.Thread(
            target=join_meeting,
            args=(email, password, meeting_link, browser, platform, self.log),
            daemon=True
        ).start()

    def create_meeting_test(self, email_entry, password_entry, node_listbox):
        browser, platform = self.get_selected_node(node_listbox)
        if browser is None:
            return
        email = email_entry.get()
        password = password_entry.get()
        threading.Thread(
            target=create_meeting,
            args=(email, password, browser, platform, self.log),
            daemon=True
        ).start()

    def refresh_nodes(self, node_listbox):
        node_listbox.delete(0, tk.END)
        self.log("Node'lar sorgulanıyor...")
        nodes = self.get_connected_nodes()
        if nodes:
            for browser, platform, ip in nodes:
                node_listbox.insert(tk.END, f"{browser} - {platform} - {ip}")
            self.log(f"{len(nodes)} node bulundu.")
        else:
            self.log("Hiçbir node bulunamadı veya hata oluştu.")

    def get_connected_nodes(self):
        nodes = []
        try:
            response = _get_local(HUB_STATUS_URL)
            if response.status_code == 200:
                value = response.json().get("value", {})
                for grid_node in value.get("nodes", []):
                    uri = grid_node.get("uri", "")
                    ip_match = re.search(r"https?://([^:/]+)", uri)
                    ip = ip_match.group(1) if ip_match else "localhost"
                    capabilities = {
                        slot.get("stereotype", {}).get("browserName")
                        for slot in grid_node.get("slots", [])
                    }
                    platform_names = {
                        slot.get("stereotype", {}).get("platformName", "MAC")
                        for slot in grid_node.get("slots", [])
                    }
                    for browser in sorted(name for name in capabilities if name):
                        platform = sorted(platform_names)[0] if platform_names else "MAC"
                        nodes.append((browser, platform, ip))
                if nodes:
                    return nodes

            # Fall back to the Selenium Grid 3 console for older external grids.
            response = _get_local(HUB_CONSOLE_URL)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for proxy in soup.find_all("div", class_="proxy"):
                    proxy_text = proxy.get_text()

                    browser_match = re.search(r"(?:Browser|browserName):\s*(\w+)", proxy_text, re.IGNORECASE)
                    browser = browser_match.group(1).strip() if browser_match else "Bilinmiyor"

                    platform_match = re.search(r"Platform:\s*(\w+)", proxy_text, re.IGNORECASE)
                    platform = platform_match.group(1).strip() if platform_match else "Bilinmiyor"

                    ip = "Bilinmiyor"
                    url_match = re.search(r"http://([\d\.]+):\d+", proxy_text)
                    if url_match:
                        ip = url_match.group(1)
                    else:
                        proxy_id = proxy.get("id", "")
                        if proxy_id:
                            ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", proxy_id)
                            if ip_match:
                                ip = ip_match.group(1)

                    nodes.append((browser, platform, ip))
        except Exception as e:
            self.log(f"Nodes alınırken hata: {e}")
        return nodes
