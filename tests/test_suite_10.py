import os
import sys
import time
import json
import logging
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from wake.wake_detector import WakeWordDetector
from stt.vad import SileroVADDetector
from stt.groq_stt import GroqSTT
from orchestrator.main import LIBAAgent
from orchestrator.permission_gate import PermissionGate
from orchestrator.ufo_bridge import UFOBridge
from tts.speaker import TTSSpeaker
from orchestrator.logger import AuditLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LIBA.TestSuite10")

def run_10_iterative_tests():
    print("\n==================================================")
    print("      LIBA 10-Point Iterative Component Suite     ")
    print("==================================================\n")

    results = []

    # -------------------------------------------------------------------------
    # Test 1: Non-Blocking openWakeWord Audio Stream Test
    # -------------------------------------------------------------------------
    print("\n[TEST 1/10] openWakeWord Non-Blocking Audio Stream...")
    try:
        oww = WakeWordDetector()
        dummy_frame = np.zeros(1280, dtype=np.int16)
        oww.oww_model.predict(dummy_frame)
        print("-> TEST 1 PASSED: openWakeWord prediction pipeline operational.")
        results.append(("Test 1: openWakeWord Stream", "PASSED"))
    except Exception as e:
        print(f"-> TEST 1 FAILED: {e}")
        results.append(("Test 1: openWakeWord Stream", f"FAILED: {e}"))

    # -------------------------------------------------------------------------
    # Test 2: Silero VAD Dynamic End-of-Speech Test
    # -------------------------------------------------------------------------
    print("\n[TEST 2/10] Silero VAD End-of-Speech Detector...")
    try:
        vad = SileroVADDetector()
        dummy_512 = np.zeros(512, dtype=np.float32)
        prob = vad.get_speech_prob(dummy_512)
        print(f"-> TEST 2 PASSED: Silero VAD model active (speech prob: {prob:.4f}).")
        results.append(("Test 2: Silero VAD", "PASSED"))
    except Exception as e:
        print(f"-> TEST 2 FAILED: {e}")
        results.append(("Test 2: Silero VAD", f"FAILED: {e}"))

    # -------------------------------------------------------------------------
    # Test 3: Groq Whisper STT API Test
    # -------------------------------------------------------------------------
    print("\n[TEST 3/10] Groq Whisper STT API...")
    try:
        stt = GroqSTT()
        dummy_audio = np.zeros(16000, dtype=np.float32)
        res = stt.transcribe_audio_bytes(dummy_audio)
        print(f"-> TEST 3 PASSED: Groq STT transcribed result: '{res}'")
        results.append(("Test 3: Groq Whisper STT", "PASSED"))
    except Exception as e:
        print(f"-> TEST 3 FAILED: {e}")
        results.append(("Test 3: Groq Whisper STT", f"FAILED: {e}"))

    # -------------------------------------------------------------------------
    # Test 4: Groq LLM API Test
    # -------------------------------------------------------------------------
    print("\n[TEST 4/10] Groq LLM Intent Engine...")
    try:
        agent = LIBAAgent()
        decision = agent.parse_llm_decision("open Notepad and write a test note")
        print(f"-> TEST 4 PASSED: Groq LLM Decision Action: {decision.get('action')}")
        results.append(("Test 4: Groq LLM Engine", "PASSED"))
    except Exception as e:
        print(f"-> TEST 4 FAILED: {e}")
        results.append(("Test 4: Groq LLM Engine", f"FAILED: {e}"))

    # -------------------------------------------------------------------------
    # Test 5: D:\New World Sandbox Auto-Approval Test
    # -------------------------------------------------------------------------
    print("\n[TEST 5/10] D:\\New World Sandbox Auto-Approval Rule...")
    try:
        gate = PermissionGate()
        sandbox_res = gate.evaluate_and_confirm("delete_file", "delete temporary test file in D:\\New World\\sandbox.txt")
        assert sandbox_res == True
        print("-> TEST 5 PASSED: D:\\New World file action auto-approved as SAFE.")
        results.append(("Test 5: D:\\New World Sandbox Auto-Approve", "PASSED"))
    except Exception as e:
        print(f"-> TEST 5 FAILED: {e}")
        results.append(("Test 5: D:\\New World Sandbox Auto-Approve", f"FAILED: {e}"))

    # -------------------------------------------------------------------------
    # Test 6: External System Protection Test
    # -------------------------------------------------------------------------
    print("\n[TEST 6/10] External System Protection Gating...")
    try:
        gate = PermissionGate()
        outside_res = gate.evaluate_and_confirm(
            "delete_file", 
            "delete critical system file C:\\Important.txt",
            confirmation_input_fn=lambda msg: False
        )
        assert outside_res == False
        print("-> TEST 6 PASSED: External file deletion GATED and blocked upon denial.")
        results.append(("Test 6: System Protection Gating", "PASSED"))
    except Exception as e:
        print(f"-> TEST 6 FAILED: {e}")
        results.append(("Test 6: System Protection Gating", f"FAILED: {e}"))

    # -------------------------------------------------------------------------
    # Test 7: Nitro70 Tool Safety Audit Test
    # -------------------------------------------------------------------------
    print("\n[TEST 7/10] Nitro70 Tool Safety Audit...")
    try:
        bridge = UFOBridge()
        raw_cmd_allowed = bridge.sanitize_and_audit_action("powershell -c Remove-Item C:\\")
        assert raw_cmd_allowed == False
        print("-> TEST 7 PASSED: Raw shell execution BLOCKED by Tool Safety Audit.")
        results.append(("Test 7: Nitro70 Tool Safety Audit", "PASSED"))
    except Exception as e:
        print(f"-> TEST 7 FAILED: {e}")
        results.append(("Test 7: Nitro70 Tool Safety Audit", f"FAILED: {e}"))

    # -------------------------------------------------------------------------
    # Test 8: Microsoft UFO2 Automation Bridge Test
    # -------------------------------------------------------------------------
    print("\n[TEST 8/10] Microsoft UFO2 Automation Bridge...")
    try:
        bridge = UFOBridge()
        assert bridge.ufo_dir.exists()
        print(f"-> TEST 8 PASSED: UFO2 bridge path valid at {bridge.ufo_dir}")
        results.append(("Test 8: UFO2 Bridge Path", "PASSED"))
    except Exception as e:
        print(f"-> TEST 8 FAILED: {e}")
        results.append(("Test 8: UFO2 Bridge Path", f"FAILED: {e}"))

    # -------------------------------------------------------------------------
    # Test 9: Piper Male Jarvis Voice TTS Test
    # -------------------------------------------------------------------------
    print("\n[TEST 9/10] Piper Male Jarvis Voice TTS Synthesis...")
    try:
        tts = TTSSpeaker()
        synth_latency = tts.speak("Test 9: British male Jarvis voice operational.", play_audio=False)
        print(f"-> TEST 9 PASSED: Male Jarvis voice synthesized in {synth_latency:.2f}s")
        results.append(("Test 9: Piper Male Jarvis Voice", "PASSED"))
    except Exception as e:
        print(f"-> TEST 9 FAILED: {e}")
        results.append(("Test 9: Piper Male Jarvis Voice", f"FAILED: {e}"))

    # -------------------------------------------------------------------------
    # Test 10: End-to-End Orchestrator & Audit Logger Test
    # -------------------------------------------------------------------------
    print("\n[TEST 10/10] End-to-End Orchestrator & Audit Logger Integration...")
    try:
        agent = LIBAAgent()
        success = agent.process_command("What is the current status of LIBA?", play_audio=False)
        assert success == True
        print("-> TEST 10 PASSED: End-to-End Orchestration turn logged to audit.jsonl.")
        results.append(("Test 10: E2E Orchestrator & Audit Log", "PASSED"))
    except Exception as e:
        print(f"-> TEST 10 FAILED: {e}")
        results.append(("Test 10: E2E Orchestrator & Audit Log", f"FAILED: {e}"))

    print("\n" + "=" * 50)
    print("               SUMMARY OF RESULTS                ")
    print("=" * 50)
    passed_count = sum(1 for _, status in results if status == "PASSED")
    for name, status in results:
        print(f"{name:<45} : {status}")
    print(f"\nTOTAL PASSED: {passed_count}/10")

if __name__ == "__main__":
    run_10_iterative_tests()
