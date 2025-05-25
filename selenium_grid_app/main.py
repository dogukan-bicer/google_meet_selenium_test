
from utils.hub import HubManager
import time
from tkinter import messagebox
from ui.tkinter_ui import SeleniumGridMeetApp

# Diğer gerekli modüller import edilir.

hub = HubManager()
def main():
    if not hub.check_hub_ready():
        print("Hub çalışmıyor, başlatılıyor...")
        hub.start_hub()
        for i in range(1, 11):
            if hub.check_hub_ready():
                print("Hub başarıyla başlatıldı!")
                break
            print(f"Bekleniyor... ({i}/10)")
            time.sleep(0.1)
        else:
            messagebox.showerror("Hata", "Hub başlatılamadı! Uygulama kapatılıyor.")
            return

    app = SeleniumGridMeetApp()
    app.mainloop()

if __name__ == "__main__":
    main()
