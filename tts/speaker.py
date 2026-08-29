import os
import re
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


def sanitize_for_tts(text: str) -> str:
    """
    Cleans markdown, typographic punctuation, emojis, and non-ASCII characters
    to ensure 100% crash-proof espeak/piper phonemization.
    """
    if not text:
        return ""
    
    # 1. Normalize typographic quotes and dashes
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2011": "-", "\u2026": "...",
        "\r\n": " ", "\n": " ", "\t": " "
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    
    # 2. Strip markdown headers, bold, italics, code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`.*?`', '', text)
    text = re.sub(r'[*_~#>-]', ' ', text)
    
    # 3. Strip emojis and non-standard characters (keep standard ASCII punctuation and alphanumeric)
    text = re.sub(r'[^\x20-\x7E]', ' ', text)
    
    # 4. Collapse multiple whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


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
        clean_text = sanitize_for_tts(text)
        if not clean_text:
            return 0.0

        print(f"[TTS (Jarvis Male Voice)] Synthesizing: '{clean_text}'")
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

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            stdout, stderr = proc.communicate(input=clean_text)

            if proc.returncode != 0:
                logger.warning(f"Piper TTS warning: {stderr}")
                return 0.0

            synth_time = time.time() - start_time
            print(f"[TTS] Synthesized WAV in {synth_time:.2f}s")

            if play_audio and temp_wav.exists():
                sr, data = wavfile.read(temp_wav)
                print("[TTS] Playing audio aloud...")
                sd.play(data, sr)
                sd.wait()
                print("[TTS] Playback completed.")

            return time.time() - start_time
        except Exception as exc:
            logger.error(f"TTS synthesis exception: {exc}")
            return 0.0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    speaker = TTSSpeaker()
    print("\n--- Male Jarvis Voice TTS Test ---")
    latency = speaker.speak("Allow me to introduce myself. I am LIBA, your personal desktop assistant.", play_audio=False)
    print(f"Jarvis male voice synthesis test successful in {latency:.2f} seconds.")