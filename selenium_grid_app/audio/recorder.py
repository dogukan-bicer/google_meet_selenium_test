# audio/recorder.py
import base64, subprocess, os, time, threading
from datetime import datetime
from utils.grid_utils import get_node_ip_from_grid
import config.config as cfg

class AudioRecorder:
    def __init__(self, driver, log_func, duration=3):
        self.driver = driver
        self.log_func = log_func
        self.duration = duration
        self.js = """
        const callback = arguments[arguments.length - 1];
        let chunks = [];
        navigator.mediaDevices.getUserMedia({ audio: true })
          .then(stream => {
            const recorder = new MediaRecorder(stream);
            recorder.ondataavailable = e => chunks.push(e.data);
            recorder.onstop = () => {
              stream.getTracks().forEach(t => t.stop());
              const blob = new Blob(chunks, { type: 'audio/webm;codecs=opus' });
              const reader = new FileReader();
              reader.onloadend = () => callback(reader.result.split(',')[1]);
              reader.readAsDataURL(blob);
            };
            recorder.start();
            setTimeout(() => recorder.stop(), 3000);
          })
          .catch(err => callback(new Error('Media error: ' + err.toString())));
        """

    def _capture(self):
        driver = cfg.driver  # Global driver'ı kullanıyoruz
        log_func = self.log_func
        if not driver:
            log_func("Driver örneği None, ses kaydı başlatılamadı.")
            return
        node_ip = get_node_ip_from_grid(driver, lambda msg: None)
        start = time.time()
        try:
            driver.set_script_timeout(self.duration + 5)
            data_b64 = driver.execute_async_script(self.js)
            audio = base64.b64decode(data_b64)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            webm = f"{node_ip}_{ts}.webm"
            mp3  = f"{node_ip}_{ts}.mp3"
            with open(webm, 'wb') as f: f.write(audio)
            subprocess.run(["ffmpeg","-y","-i", webm, mp3], check=True)
            os.remove(webm)
            latency = int((time.time() - start)*1000)
            log_func(f"Ses kaydı tamamlandı: {mp3} (Gecikme: {latency} ms)", ip=node_ip)
            return mp3
        except Exception as e:
            latency = int((time.time() - start)*1000)
            log_func(f"[!] Ses kaydı hatası: {e} (Gecikme: {latency} ms)", ip=node_ip)
            return None

    def record_async(self):
        threading.Thread(target=self._capture, daemon=True).start()
