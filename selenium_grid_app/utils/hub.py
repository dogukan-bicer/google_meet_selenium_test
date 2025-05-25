import os
import re
import time
import threading
import subprocess
import requests
import tkinter as tk
from tkinter import messagebox
from bs4 import BeautifulSoup
from utils.logging import global_log_message
from config.config import HUB_COMMAND, HUB_DIR, HUB_WD_URL, HUB_CONSOLE_URL
from drivers.remote_driver import join_meeting, create_meeting

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
        self.log("Selenium Hub başlatılıyor...")
        try:
            subprocess.Popen(HUB_COMMAND, cwd=HUB_DIR, shell=True)
            time.sleep(5)
            self.log("Selenium Hub başlatıldı.")
        except Exception as e:
            self.log(f"Hub başlatılırken hata: {e}")

    def check_hub_ready(self):
        status_url = f"{HUB_WD_URL}/status"
        try:
            response = requests.get(status_url, timeout=5)
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
            response = requests.get(HUB_CONSOLE_URL, timeout=5)
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
