import os
import io
import sys
import time
import logging
from pathlib import Path
import numpy as np
import scipy.io.wavfile as wavfile
from dotenv import load_dotenv
import groq

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

class GroqSTT:
    """
    Speech-To-Text transcriber using Groq's hosted Whisper large-v3-turbo API.
    """
    def __init__(self, model_name: str = "whisper-large-v3-turbo"):
        self.model_name = model_name
        self.api_key = os.getenv("GROQ_API_KEY")
        if self.api_key:
            self.client = groq.Groq(api_key=self.api_key)
            logger.info(f"Initialized Groq STT with model '{self.model_name}'")
        else:
            self.client = None
            logger.warning("GROQ_API_KEY not found in environment. Falling back to local whisper if needed.")

        # Local fallback lazy loader
        self._local_whisper = None

    def _get_local_whisper(self):
        if not self._local_whisper:
            from stt.listener import STTListener
            self._local_whisper = STTListener(model_size="base.en")
        return self._local_whisper

    def transcribe_audio_bytes(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcribes a numpy array of audio PCM float32 samples to text via Groq Whisper API.
        """
        start_time = time.time()

        if self.client:
            try:
                # Convert float32 numpy array to 16-bit int PCM WAV bytes
                audio_int16 = (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)
                wav_buffer = io.BytesIO()
                wavfile.write(wav_buffer, sample_rate, audio_int16)
                wav_buffer.seek(0)
                wav_buffer.name = "input_audio.wav"

                # Send to Groq Whisper endpoint
                response = self.client.audio.transcriptions.create(
                    file=(wav_buffer.name, wav_buffer.read(), "audio/wav"),
                    model=self.model_name,
                    response_format="text",
                    language="en"
                )
                text = str(response).strip()
                latency = time.time() - start_time
                print(f"[Groq STT] Transcribed via Groq Whisper ({self.model_name}) in {latency:.2f}s")
                return text
            except Exception as e:
                logger.error(f"Groq STT API error: {e}. Attempting local fallback...")

        # Offline fallback
        local_stt = self._get_local_whisper()
        return local_stt.transcribe(audio_data)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    stt = GroqSTT()
    print("--- Step 3 Groq STT Module Test ---")
    dummy_audio = np.zeros(16000, dtype=np.float32)
    result = stt.transcribe_audio_bytes(dummy_audio)
    print(f"STT Result: '{result}'")
