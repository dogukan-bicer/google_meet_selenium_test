# -----------------------------
# Global Log Fonksiyonu
# -----------------------------

import time
import tkinter as tk

def global_log_message(text, widget, ip=None):
    """Mesajı konsola ve widget'a IP bilgisi ile yazar."""
    timestamp = time.strftime("%H:%M:%S")
    ip_info = f"[{ip}] " if ip else "[IP Yok] "
    msg = f"{timestamp} - {ip_info}{text}"
    if widget is None:
        print(msg)
    else:
        widget.configure(state="normal")
        widget.insert(tk.END, msg + "\n")
        widget.configure(state="disabled")
        widget.see(tk.END)