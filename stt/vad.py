import time
import logging
import numpy as np
import sounddevice as sd
import onnxruntime as ort
import openwakeword
from pathlib import Path

logger = logging.getLogger(__name__)

OWW_RESOURCES_DIR = Path(openwakeword.__file__).parent / "resources" / "models"
SILERO_ONNX_PATH = OWW_RESOURCES_DIR / "silero_vad.onnx"

class SileroVADDetector:
    """
    Voice Activity Detection (VAD) using Silero VAD ONNX model.
    Detects dynamic end-of-speech so recording stops as soon as user stops speaking.
    """
    def __init__(self, model_path: Path = SILERO_ONNX_PATH):
        self.sample_rate = 16000
        self.window_size_samples = 512 # 32ms frames at 16kHz
        self.model_path = model_path
        
        if self.model_path.exists():
            logger.info(f"Loading Silero VAD ONNX model from {self.model_path}")
            self.session = ort.InferenceSession(str(self.model_path), providers=['CPUExecutionProvider'])
            self._reset_state()
            self.has_model = True
        else:
            logger.warning(f"Silero VAD ONNX model not found at {self.model_path}, using energy-based VAD fallback.")
            self.has_model = False

    def _reset_state(self):
        self._h = np.zeros((2, 1, 64), dtype=np.float32)
        self._c = np.zeros((2, 1, 64), dtype=np.float32)

    def get_speech_prob(self, frame_pcm: np.ndarray) -> float:
        """
        Compute speech probability for a 512-sample PCM float32 frame.
        """
        if not self.has_model:
            rms = np.sqrt(np.mean(frame_pcm**2))
            return 1.0 if rms > 0.01 else 0.0

        if len(frame_pcm) != self.window_size_samples:
            frame_pcm = np.pad(frame_pcm, (0, self.window_size_samples - len(frame_pcm)))

        input_data = np.expand_dims(frame_pcm, axis=0).astype(np.float32)
        sr_data = np.array(self.sample_rate, dtype=np.int64)

        try:
            inputs = {
                'input': input_data,
                'sr': sr_data,
                'h': self._h,
                'c': self._c
            }
            out, self._h, self._c = self.session.run(None, inputs)
            return float(out[0][0])
        except Exception as e:
            logger.debug(f"VAD inference exception: {e}")
            rms = np.sqrt(np.mean(frame_pcm**2))
            return 1.0 if rms > 0.01 else 0.0

    def record_until_speech_ends(
        self,
        silence_threshold_sec: float = 0.8,
        max_duration_sec: float = 12.0,
        vad_prob_threshold: float = 0.45
    ) -> np.ndarray:
        """
        Stream audio from microphone using InputStream.read() and stop automatically when user finishes speaking.
        """
        print(f"\n[VAD LISTENER] Recording... Speak now! (Auto-stops after {silence_threshold_sec}s silence)")
        self._reset_state()

        recorded_chunks = []
        speech_started = False
        silence_start_time = None
        start_time = time.time()

        chunk_samples = 512
        
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='float32') as stream:
                while True:
                    elapsed = time.time() - start_time
                    if elapsed > max_duration_sec:
                        print(f"[VAD LISTENER] Max duration ({max_duration_sec}s) reached.")
                        break

                    # Correct stream read invocation returning (frame_data, overflowed)
                    frame_data, overflowed = stream.read(chunk_samples)
                    frame = frame_data.flatten()
                    recorded_chunks.append(frame)

                    prob = self.get_speech_prob(frame)

                    if prob >= vad_prob_threshold:
                        if not speech_started:
                            print("[VAD LISTENER] Speech detected!")
                            speech_started = True
                        silence_start_time = None
                    else:
                        if speech_started:
                            if silence_start_time is None:
                                silence_start_time = time.time()
                            elif (time.time() - silence_start_time) >= silence_threshold_sec:
                                print(f"[VAD LISTENER] End of speech detected ({silence_threshold_sec}s silence). Stopping recording!")
                                break
        except Exception as e:
            logger.error(f"VAD stream recording error: {e}")

        if recorded_chunks:
            return np.concatenate(recorded_chunks)
        return np.zeros(self.sample_rate, dtype=np.float32)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    vad = SileroVADDetector()
    print("--- Silero VAD Stream Test ---")
    dummy_frame = np.zeros(512, dtype=np.float32)
    prob = vad.get_speech_prob(dummy_frame)
    print(f"VAD dummy frame speech probability: {prob:.4f}")
