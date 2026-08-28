#!/usr/bin/env python
import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from orchestrator.main import LIBAAgent
from orchestrator.background_service import LIBABackgroundService
from hermes.hermes_agent import HermesVoiceAgent

def main():
    parser = argparse.ArgumentParser(description="LIBA / Hermes Agent — Local Windows Desktop Voice Assistant (Groq + openWakeWord + Silero VAD)")
    parser.add_argument("--mode", "-m", choices=["background", "command", "voice"], default="background",
                        help="Operating mode: 'background' for continuous hands-free wake loop ('LIBA' / 'Hey Jarvis'), 'command' for text prompt, 'voice' for single turn.")
    parser.add_argument("--text", "-t", type=str, default="", help="Command text for 'command' mode.")
    parser.add_argument("--agent", "-a", choices=["liba", "hermes"], default="hermes",
                        help="Agent architecture to use: 'hermes' for Hermes autonomous tool-calling agent, 'liba' for standard orchestrator.")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    print("==================================================")
    print(f"      Hermes Voice Agent Initializing ({args.agent.upper()} Mode) ")
    print("==================================================")

    if args.mode == "background":
        service = LIBABackgroundService()
        service.start_continuous_loop()

    elif args.mode == "command":
        if not args.text:
            print("Error: --text parameter required for 'command' mode.")
            sys.exit(1)
        if args.agent == "hermes":
            hermes = HermesVoiceAgent()
            hermes.run_agent_turn(args.text, play_audio=True)
        else:
            agent = LIBAAgent()
            agent.process_command(args.text, play_audio=True)

    elif args.mode == "voice":
        if args.agent == "hermes":
            hermes = HermesVoiceAgent()
            # Record voice turn using Silero VAD
            from stt.vad import SileroVADDetector
            vad = SileroVADDetector()
            audio_samples = vad.record_until_speech_ends()
            text = hermes.stt.transcribe_audio_bytes(audio_samples)
            if text:
                hermes.run_agent_turn(text, play_audio=True)
        else:
            service = LIBABackgroundService()
            service.run_single_interaction_turn()

if __name__ == "__main__":
    main()
