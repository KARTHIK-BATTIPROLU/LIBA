import json
import logging
import time
from pathlib import Path
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

class STTListener:
    """
    Local Speech-To-Text listener using faster-whisper.
    """
    def __init__(self, model_size: str = "base.en", device: str = "cpu", compute_type: str = "int8"):
        logger.info(f"Loading faster-whisper model '{model_size}' on {device} ({compute_type})...")
        start_time = time.time()
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info(f"Whisper model loaded in {time.time() - start_time:.2f}s")
        self.sample_rate = 16000

    def record_audio(self, duration: float = 4.0, sample_rate: int = 16000) -> np.ndarray:
        """
        Record audio from the default microphone for a fixed duration.
        """
        print(f"\n[STT] Recording for {duration} seconds... Speak now!")
        audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
        sd.wait()
        print("[STT] Recording finished.")
        return audio.flatten()

    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribe raw float32 audio numpy array to text.
        """
        start_time = time.time()
        segments, info = self.model.transcribe(audio_data, beam_size=5, language="en")
        text = " ".join([segment.text.strip() for segment in segments])
        latency = time.time() - start_time
        print(f"[STT] Transcribed in {latency:.2f}s (Detected lang: {info.language}, prob: {info.language_probability:.2f})")
        return text

    def record_and_transcribe(self, duration: float = 4.0) -> str:
        """
        Convenience method to record and transcribe audio in one call.
        """
        audio = self.record_audio(duration=duration)
        text = self.transcribe(audio)
        return text

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    stt = STTListener(model_size="base.en")
    print("\n--- STT Module Test ---")
    print("Testing Whisper STT pipeline on dummy audio input...")
    # Generate 1 second of silence for automated pipeline check
    dummy_audio = np.zeros(16000, dtype=np.float32)
    res = stt.transcribe(dummy_audio)
    print(f"Dummy Transcription Result: '{res}'")
