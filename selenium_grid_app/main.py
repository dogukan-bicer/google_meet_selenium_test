
from ui.tkinter_ui import SeleniumGridMeetApp
import threading


def wait_for_grid(app, attempts=0):
    if app.hub_manager.check_hub_ready():
        app.log_message("Selenium Grid hazır; yerel Brave node'u bağlandı.")
        app.hub_manager.refresh_nodes(app.node_list)
        return
    if attempts >= 60:
        app.log_message("Grid henüz hazır değil. selenium-meet-grid.log dosyasını kontrol edin.")
        return
    app.after(1000, wait_for_grid, app, attempts + 1)

def main():
    app = SeleniumGridMeetApp()
    if app.hub_manager.check_hub_ready():
        app.log_message("Selenium Grid bağlantısı hazır.")
        app.hub_manager.refresh_nodes(app.node_list)
    else:
        app.log_message(
            "Yerel Grid bulunamadı; bu bilgisayardaki Brave node'u başlatılıyor..."
        )
        threading.Thread(target=app.hub_manager.start_hub, daemon=True).start()
        app.after(1000, wait_for_grid, app)
    app.mainloop()

if __name__ == "__main__":
    main()
