import sys
import time
import logging
import winsound
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from wake.wake_detector import WakeWordDetector
from stt.vad import SileroVADDetector
from hermes.hermes_agent import HermesVoiceAgent

logger = logging.getLogger("Hermes.BackgroundService")

def play_chime():
    """
    Play a brief audio chime on wake detection.
    """
    try:
        winsound.Beep(880, 150) # 880Hz A5 note for 150ms
        time.sleep(0.05)
        winsound.Beep(1320, 200) # 1320Hz E6 note for 200ms
    except Exception as e:
        logger.debug(f"Audio chime exception: {e}")

class LIBABackgroundService:
    """
    Continuous hands-free background voice service powering Hermes Voice Agent.
    """
    def __init__(self):
        self.wake_detector = WakeWordDetector(threshold=0.20)
        self.vad = SileroVADDetector()
        self.hermes = HermesVoiceAgent()
        self.is_running = True

    def run_single_interaction_turn(self):
        """
        Runs one complete voice turn: VAD recording -> Groq STT -> Hermes Agent -> Piper Male TTS.
        """
        play_chime()
        print("\n" + "=" * 50)
        print("[HERMES ACTIVATED] Listening... Speak your request now!")
        
        # Record audio until end of speech detected by Silero VAD
        audio_samples = self.vad.record_until_speech_ends(silence_threshold_sec=0.8, max_duration_sec=12.0)
        
        if len(audio_samples) < 4000: # Less than 0.25s of audio
            print("[HERMES]: No speech captured.")
            return

        # Groq STT Transcription
        user_transcript = self.hermes.stt.transcribe_audio_bytes(audio_samples)
        if not user_transcript or not user_transcript.strip():
            print("[HERMES]: Could not transcribe audio.")
            return

        # Process through Hermes Agent (Tools -> UFO2 -> Gate -> TTS)
        self.hermes.run_agent_turn(user_transcript, play_audio=True)

    def start_continuous_loop(self):
        """
        Starts the continuous hands-free idle listening loop.
        """
        print("\n==================================================")
        print("  Hermes Voice Agent Active & Listening Live!     ")
        print(" Speak anytime — say 'LIBA' or 'Hey Jarvis'!     ")
        print(" Press Ctrl+C in terminal to stop.                ")
        print("==================================================\n")

        while self.is_running:
            try:
                # 1. High-sensitivity listening for speech / wake word
                triggered = self.wake_detector.listen_for_wake()
                if triggered:
                    # 2. Execute Hermes Voice Agent turn
                    self.run_single_interaction_turn()
            except KeyboardInterrupt:
                print("\n[HERMES] Stopping background service. Goodbye!")
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"Error in background wake loop: {e}", exc_info=True)
                time.sleep(1.0)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    service = LIBABackgroundService()
    print("--- Hermes Background Service Test ---")
    service.run_single_interaction_turn()
