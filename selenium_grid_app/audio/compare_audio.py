import os
import threading
import librosa
import tensorflow as tf
import tensorflow_hub as hub
from scipy.spatial.distance import cosine

class AudioComparer:
    """
    TRILLsson tabanlı ses kalitesi karşılaştırma sınıfı.
    """
    # Modeli sınıf yüklenirken bir kez yükle
    _trill_model = hub.load("https://tfhub.dev/google/nonsemantic-speech-benchmark/trill/3")

    def __init__(self, log_func, label_widget=None, sample_rate=16000):
        self.log_func = log_func
        self.label_widget = label_widget
        self.sample_rate = sample_rate

    @staticmethod
    def _load_audio(file_path, sr):
        return librosa.load(file_path, sr=sr, mono=True)

    @classmethod
    def compare_audio_files(cls, file1, file2, sample_rate=16000):
        try:
            ref, _ = cls._load_audio(file1, sample_rate)
            deg, _ = cls._load_audio(file2, sample_rate)

            ref_tensor = tf.convert_to_tensor(ref, dtype=tf.float32)[tf.newaxis, :]
            deg_tensor = tf.convert_to_tensor(deg, dtype=tf.float32)[tf.newaxis, :]

            ref_embed = cls._trill_model(samples=ref_tensor, sample_rate=sample_rate)["embedding"]
            deg_embed = cls._trill_model(samples=deg_tensor, sample_rate=sample_rate)["embedding"]

            ref_vec = tf.reduce_mean(ref_embed, axis=1).numpy().squeeze()
            deg_vec = tf.reduce_mean(deg_embed, axis=1).numpy().squeeze()

            similarity = 1 - cosine(ref_vec, deg_vec)
            return max(similarity * 100, 0), None
        except Exception as e:
            return None, f"TRILL embed hata: {e}"

    def compare(self):
        """UI'dan çağrılan karşılaştırma metodu, en son iki dosyayı otomatik seçer."""
        threading.Thread(target=self._task, daemon=True).start()

    def _task(self):
        audio_files = sorted(
            [f for f in os.listdir('.') if f.endswith('.mp3')],
            key=os.path.getmtime,
            reverse=True
        )[:2]
        if len(audio_files) < 2:
            self.log_func("Karşılaştırma için en az iki ses kaydı gerekli!")
            return

        file1, file2 = audio_files
        self.log_func(f"Karşılaştırılan dosyalar: {file1}, {file2}")
        score, error = self.compare_audio_files(file1, file2, self.sample_rate)

        if score is not None:
            ip1 = file1.split('_')[0]
            ip2 = file2.split('_')[0]
            msg = f"TRILLsson Skoru ({ip1} vs {ip2}): {score:.2f}"
            if self.label_widget:
                self.label_widget.config(text=msg)
            self.log_func(msg)
        else:
            self.log_func(f"Hata: {error}")
