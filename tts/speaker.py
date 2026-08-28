import os
import sys
import time
import logging
import subprocess
from pathlib import Path
import requests
import sounddevice as sd
import scipy.io.wavfile as wavfile

logger = logging.getLogger(__name__)

# Male British voice model (Jarvis accent)
VOICE_MODEL_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx"
VOICE_CONFIG_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json"

class TTSSpeaker:
    """
    Local Text-To-Speech speaker using Piper TTS (Male Jarvis-like British voice).
    """
    def __init__(self, tts_dir: str = "tts"):
        self.tts_dir = Path(tts_dir)
        self.tts_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.tts_dir / "en_GB-alan-medium.onnx"
        self.config_path = self.tts_dir / "en_GB-alan-medium.onnx.json"
        self._ensure_model_exists()

    def _download_file(self, url: str, target_path: Path):
        if not target_path.exists():
            logger.info(f"Downloading male Jarvis TTS voice model from {url}...")
            resp = requests.get(url, stream=True)
            resp.raise_for_status()
            with open(target_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Saved male voice asset to {target_path}")

    def _ensure_model_exists(self):
        self._download_file(VOICE_MODEL_URL, self.model_path)
        self._download_file(VOICE_CONFIG_URL, self.config_path)

    def speak(self, text: str, play_audio: bool = True) -> float:
        """
        Synthesize text to audio using British male voice and play aloud. Returns total latency in seconds.
        """
        if not text or not text.strip():
            return 0.0

        # Sanitize text to remove surrogate characters and unencodable symbols
        text = text.encode('utf-8', 'ignore').decode('utf-8')
        text = ''.join(c for c in text if ord(c) < 0xD800 or ord(c) > 0xDFFF)

        print(f"[TTS (Jarvis Male Voice)] Synthesizing: '{text}'")
        start_time = time.time()
        temp_wav = self.tts_dir / "temp_output.wav"

        cmd = [
            sys.executable,
            "-m",
            "piper",
            "-m",
            str(self.model_path),
            "-c",
            str(self.config_path),
            "-f",
            str(temp_wav)
        ]

        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
        stdout, stderr = proc.communicate(input=text)

        if proc.returncode != 0:
            logger.error(f"Piper TTS error: {stderr}")
            raise RuntimeError(f"Piper TTS synthesis failed: {stderr}")

        synth_time = time.time() - start_time
        print(f"[TTS] Synthesized WAV in {synth_time:.2f}s")

        if play_audio and temp_wav.exists():
            sr, data = wavfile.read(temp_wav)
            print("[TTS] Playing audio aloud...")
            sd.play(data, sr)
            sd.wait()
            print("[TTS] Playback completed.")

        return time.time() - start_time

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    speaker = TTSSpeaker()
    print("\n--- Male Jarvis Voice TTS Test ---")
    latency = speaker.speak("Allow me to introduce myself. I am LIBA, your personal desktop assistant.", play_audio=False)
    print(f"Jarvis male voice synthesis test successful in {latency:.2f} seconds.")
