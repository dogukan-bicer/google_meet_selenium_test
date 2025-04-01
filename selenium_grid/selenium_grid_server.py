import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import requests
import subprocess
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup  # HTML parse işlemi için

# Ayarlar
HUB_HOST = "192.168.1.22"
HUB_PORT = "4444"
HUB_URL = f"http://{HUB_HOST}:{HUB_PORT}"
HUB_WD_URL = f"{HUB_URL}/wd/hub"
HUB_CONSOLE_URL = f"{HUB_URL}/grid/console"
HUB_DIR = r"C:\Users\doguk\Downloads\selenium-server-3.7.0"
HUB_COMMAND = "java -jar selenium-server-standalone-3.7.1.jar -role hub"

def log_message(text, widget):
    """Log mesajını Tkinter widget'ına veya konsola yazar."""
    if widget is None:
        print(text)
    else:
        widget.configure(state='normal')
        widget.insert(tk.END, f"{text}\n")
        widget.configure(state='disabled')
        widget.yview(tk.END)

def start_hub(log_widget):
    """Selenium Hub'ı başlatır."""
    log_message("Selenium Hub başlatılıyor...", log_widget)
    try:
        subprocess.Popen(HUB_COMMAND, cwd=HUB_DIR, shell=True)
        time.sleep(15)  # Hub'ın tamamen başlaması için bekleme süresi
        log_message("Selenium Hub başlatıldı.", log_widget)
    except Exception as e:
        log_message(f"Hub başlatılırken hata: {str(e)}", log_widget)

def check_hub_ready():
    """Hub'ın hazır olup olmadığını kontrol eder."""
    status_url = f"{HUB_WD_URL}/status"
    try:
        response = requests.get(status_url, timeout=10)
        return response.status_code == 200
    except Exception:
        return False

def get_connected_nodes():
    """
    Selenium Grid Console sayfasını çekerek bağlı node’ları HTML parse yöntemiyle alır.
    Her node için (browser, platform) bilgisi listeye eklenir.
    """
    nodes = []
    try:
        response = requests.get(HUB_CONSOLE_URL, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Her node bilgisinin <div class="proxy"> etiketi içinde olduğunu varsayıyoruz
            for proxy in soup.find_all("div", class_="proxy"):
                proxy_text = proxy.get_text()
                # Browser bilgisini çekmek için
                browser_match = re.search(r"(?:Browser|browserName):\s*(\w+)", proxy_text, re.IGNORECASE)
                if browser_match:
                    browser = browser_match.group(1).strip()
                else:
                    browser = "Bilinmiyor"
                # Platform bilgisini çekmek için
                platform_match = re.search(r"Platform:\s*(\w+)", proxy_text, re.IGNORECASE)
                if platform_match:
                    platform = platform_match.group(1).strip()
                else:
                    platform = "Bilinmiyor"
                nodes.append((browser, platform))
    except Exception as e:
        print(f"Nodes alınırken hata: {str(e)}")
    return nodes

def run_test(browser, platform, log_widget):
    """
    Belirtilen browser ve platform için test senaryosunu çalıştırır.
    Belirtilen tarayıcıdan Google açılarak yüklenme süresi ölçülür.
    """
    chrome_options = Options()
    chrome_options.set_capability("browserName", browser)
    chrome_options.set_capability("platformName", platform)

    log_message(f"{browser} / {platform} testi başlatılıyor...", log_widget)
    try:
        driver = webdriver.Remote(
            command_executor=HUB_WD_URL,
            options=chrome_options
        )
        start_time = time.time()
        driver.get("https://www.google.com")
        load_time = time.time() - start_time
        log_message(f"{browser} / {platform} üzerinde Google {load_time:.2f} saniyede açıldı.", log_widget)
        driver.quit()
    except Exception as e:
        log_message(f"{browser} / {platform} testinde hata: {str(e)}", log_widget)

class SeleniumGridApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Selenium Grid Node Test Arayüzü")
        self.geometry("600x400")

        # Üst Frame: Düğmeler ve liste kutusu
        top_frame = ttk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=10, pady=5)

        refresh_btn = ttk.Button(top_frame, text="Node'ları Yenile", command=self.refresh_nodes)
        refresh_btn.grid(row=0, column=0, padx=5)

        test_btn = ttk.Button(top_frame, text="Seçili Node Testi", command=self.test_selected_node)
        test_btn.grid(row=0, column=1, padx=5)

        self.node_list = tk.Listbox(top_frame, height=5, width=50)
        self.node_list.grid(row=1, column=0, columnspan=2, pady=5)

        # Alt Frame: Log ekranı
        self.log_text = scrolledtext.ScrolledText(self, state='disabled', height=15)
        self.log_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # İlk node'ları yükle
        self.refresh_nodes()

    def refresh_nodes(self):
        """Node listesini günceller."""
        self.node_list.delete(0, tk.END)
        log_message("Node'lar sorgulanıyor...", self.log_text)
        nodes = get_connected_nodes()
        if nodes:
            for browser, platform in nodes:
                self.node_list.insert(tk.END, f"{browser} - {platform}")
            log_message(f"{len(nodes)} node bulundu.", self.log_text)
        else:
            log_message("Hiçbir node bulunamadı veya sorguda hata oluştu.", self.log_text)

    def test_selected_node(self):
        """Listeden seçilen node için test senaryosunu başlatır."""
        selection = self.node_list.curselection()
        if not selection:
            messagebox.showwarning("Uyarı", "Lütfen test etmek için bir node seçin!")
            return
        selected_text = self.node_list.get(selection[0])
        try:
            # Seçilen metin "browser - platform" formatındadır.
            parts = selected_text.split("-")
            if len(parts) < 2:
                raise ValueError("Seçilen node bilgileri eksik")
            browser = parts[0].strip()
            platform = parts[1].strip()
        except Exception as e:
            messagebox.showerror("Hata", f"Seçilen node bilgileri okunamadı: {str(e)}")
            return

        threading.Thread(target=run_test, args=(browser, platform, self.log_text), daemon=True).start()

def main():
    if not check_hub_ready():
        print("Hub çalışmıyor, başlatılıyor...")
        start_hub(log_widget=None)
        for i in range(1, 11):
            if check_hub_ready():
                print("Hub başarıyla başlatıldı!")
                break
            print(f"Bekleniyor... ({i}/10)")
            time.sleep(5)
        else:
            messagebox.showerror("Hata", "Hub başlatılamadı! Uygulama kapatılıyor.")
            return

    app = SeleniumGridApp()
    app.mainloop()

if __name__ == "__main__":
    # Uygulama çalıştırıldığında http://192.168.1.22:4444/grid/console adresinden node bilgileri çekilecektir.
    main()
