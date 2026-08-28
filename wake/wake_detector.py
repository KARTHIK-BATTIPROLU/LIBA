import time
import queue
import logging
import numpy as np
import sounddevice as sd
from openwakeword.model import Model

logger = logging.getLogger("LIBA.WakeWord")

class WakeWordDetector:
    """
    High-sensitivity openWakeWord detector + Speech Energy trigger.
    """
    def __init__(self, target_models: list = None, threshold: float = 0.20):
        self.target_models = target_models or ["hey_jarvis", "alexa", "hey_mycroft", "hey_rhasspy"]
        self.threshold = threshold
        logger.info(f"Initializing high-sensitivity openWakeWord detector (threshold={self.threshold})")
        self.oww_model = Model(wakeword_models=self.target_models, inference_framework="onnx")
        self.sample_rate = 16000
        self.chunk_size = 1280 # 80ms chunks at 16kHz

    def listen_for_wake(self, timeout: float = None) -> bool:
        """
        Listens on microphone stream queue. Triggers on openWakeWord score >= threshold
        OR speech energy detection.
        """
        print(f"\n[WAKE WORD LISTENER] Listening for speech / wake word... ('LIBA' or 'Hey Jarvis')")
        start_time = time.time()
        audio_queue = queue.Queue()

        def audio_callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"Audio stream status: {status}")
            audio_queue.put(indata.copy())

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='int16',
                blocksize=self.chunk_size,
                callback=audio_callback
            ):
                consecutive_speech_frames = 0
                while True:
                    if timeout and (time.time() - start_time) > timeout:
                        return False

                    try:
                        chunk_data = audio_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    audio_frame = chunk_data.flatten()

                    # 1. Check openWakeWord prediction scores
                    prediction = self.oww_model.predict(audio_frame)
                    for model_name, score in self.oww_model.prediction_buffer.items():
                        current_score = score[-1] if len(score) > 0 else 0.0
                        if current_score >= self.threshold:
                            print(f"\n[WAKE WORD TRIGGERED!] openWakeWord model '{model_name}' (score: {current_score:.2f})")
                            self.oww_model.reset()
                            return True

                    # 2. Check Audio Speech Energy (RMS) fallback trigger
                    audio_float = audio_frame.astype(np.float32) / 32768.0
                    rms = np.sqrt(np.mean(audio_float**2))
                    if rms > 0.025: # Speech volume threshold
                        consecutive_speech_frames += 1
                        if consecutive_speech_frames >= 2: # 160ms of continuous speech
                            print(f"\n[SPEECH DETECTED!] Audio energy trigger (RMS: {rms:.4f})")
                            self.oww_model.reset()
                            return True
                    else:
                        consecutive_speech_frames = max(0, consecutive_speech_frames - 1)

        except Exception as e:
            logger.error(f"Wake word stream exception: {e}")
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    detector = WakeWordDetector()
    print("--- High-Sensitivity Wake Word Detector Test ---")
    dummy_frame = np.zeros(1280, dtype=np.int16)
    detector.oww_model.predict(dummy_frame)
    print("High-sensitivity wake detector ready.")
