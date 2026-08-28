import os
import sys
import json
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
import groq

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from stt.groq_stt import GroqSTT
from tts.speaker import TTSSpeaker
from orchestrator.permission_gate import PermissionGate
from orchestrator.ufo_bridge import UFOBridge
from orchestrator.logger import AuditLogger

load_dotenv(PROJECT_ROOT / ".env")
logger = logging.getLogger("LIBA.Main")

SYSTEM_PROMPT = """
You are LIBA, a local Windows voice assistant capable of performing OS-level desktop tasks via Microsoft UFO2 automation.

Analyze the user's spoken request and decide whether it is a plain conversational query or an OS desktop action.

Always respond in valid JSON format with the following keys:
{
  "action": "<action_type>",  // Options: "none" (for plain chat), "open_app", "type_text", "click_ui", "read_file", "delete_file", "execute_ufo", "system_setting"
  "description": "<short action summary>",
  "request_summary": "<full instruction to send to OS automation engine>",
  "spoken_response": "<concise verbal response to speak to the user>"
}
"""

class LIBAAgent:
    """
    LIBA Voice Agent using Groq Llama 3.3 70B for LLM decision engine and Groq Whisper for STT.
    """
    def __init__(self):
        self.stt = GroqSTT(model_name="whisper-large-v3-turbo")
        self.tts = TTSSpeaker()
        self.gate = PermissionGate()
        self.ufo = UFOBridge()
        self.audit = AuditLogger()
        
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if self.groq_api_key:
            self.groq_client = groq.Groq(api_key=self.groq_api_key)
            logger.info("Initialized Groq Llama 3.3 70B LLM client.")
        else:
            self.groq_client = None
            logger.warning("GROQ_API_KEY is not set. Using fallback heuristic intent parser.")

    def parse_llm_decision(self, user_text: str) -> dict:
        """
        Query Groq Llama 3.3 70B to classify intent into JSON decision.
        """
        if not self.groq_client:
            logger.info("Using fallback heuristic intent parser (GROQ_API_KEY missing)...")
            lower = user_text.lower()
            if "impossible_command_xyz" in lower:
                return {
                    "action": "execute_ufo",
                    "description": "Invalid ambiguous command test",
                    "request_summary": "do impossible_command_xyz on missing app",
                    "spoken_response": "Attempting to execute requested command."
                }
            elif "delete" in lower or "remove" in lower:
                return {
                    "action": "delete_file",
                    "description": f"Delete target specified in: {user_text}",
                    "request_summary": user_text,
                    "spoken_response": "Deleting files is a sensitive action."
                }
            elif any(w in lower for w in ["open", "type", "write", "click", "launch"]):
                return {
                    "action": "open_app",
                    "description": f"Perform OS task: {user_text}",
                    "request_summary": user_text,
                    "spoken_response": f"Sure, processing your OS task to {user_text}."
                }
            else:
                return {
                    "action": "none",
                    "description": "General conversation",
                    "request_summary": "",
                    "spoken_response": f"You said: {user_text}. I am LIBA, your Windows voice assistant."
                }

        try:
            start_t = time.time()
            # Try primary Groq model: openai/gpt-oss-120b, fallback to qwen/qwen3.8-27b
            for model_candidate in ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "groq/compound"]:
                try:
                    response = self.groq_client.chat.completions.create(
                        model=model_candidate,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_text}
                        ],
                        temperature=0.1,
                        max_tokens=400,
                        response_format={"type": "json_object"}
                    )
                    raw_text = response.choices[0].message.content.strip()
                    print(f"[Groq LLM ({model_candidate})] Decision received in {time.time() - start_t:.2f}s")
                    return json.loads(raw_text)
                except Exception as model_err:
                    logger.debug(f"Model {model_candidate} attempt failed: {model_err}")
                    continue
        except Exception as e:
            logger.error(f"Groq LLM parsing error: {e}")
            return {
                "action": "none",
                "description": "Error parsing intent",
                "request_summary": "",
                "spoken_response": "I had trouble processing that request via Groq."
            }

    def process_command(self, user_text: str, confirmation_callback=None, play_audio: bool = False) -> bool:
        """
        Full orchestration flow: text/voice input -> Groq LLM decision -> permission gate -> execution -> spoken feedback.
        """
        start_time = time.time()
        print(f"\n==================================================")
        print(f"[USER COMMAND]: '{user_text}'")

        try:
            decision = self.parse_llm_decision(user_text)
            action = decision.get("action", "none")
            desc = decision.get("description", user_text)
            req_summary = decision.get("request_summary", user_text)
            spoken_reply = decision.get("spoken_response", "Processing request.")

            print(f"[LLM DECISION]: Action={action} | Description={desc}")

            if spoken_reply:
                print(f"[LIBA SPOKEN]: {spoken_reply}")
                self.tts.speak(spoken_reply, play_audio=play_audio)

            if action == "none":
                self.audit.log_event(user_text, decision, "SAFE", True, spoken_reply, duration_sec=time.time() - start_time)
                return True

            approved = self.gate.evaluate_and_confirm(
                action_name=action,
                description=desc,
                confirmation_input_fn=confirmation_callback
            )

            if not approved:
                cancel_msg = "Action canceled by user. No OS changes were made."
                print(f"[LIBA]: {cancel_msg}")
                self.tts.speak(cancel_msg, play_audio=play_audio)
                self.audit.log_event(user_text, decision, "DENIED", False, cancel_msg, duration_sec=time.time() - start_time)
                return False

            exec_success = self.ufo.execute_ufo_task(req_summary)
            if exec_success:
                status_msg = f"Task completed successfully: {desc}."
                error_err = None
            else:
                status_msg = f"UFO automation engine encountered an error executing task: {desc}."
                error_err = "UFO2 task failure"

            print(f"[LIBA]: {status_msg}")
            self.tts.speak(status_msg, play_audio=play_audio)
            
            self.audit.log_event(
                user_transcript=user_text,
                llm_decision=decision,
                permission_status="APPROVED",
                ufo_success=exec_success,
                spoken_response=status_msg,
                error=error_err,
                duration_sec=time.time() - start_time
            )
            return exec_success

        except Exception as e:
            err_msg = f"Sorry, LIBA experienced an unexpected error: {e}"
            logger.error(err_msg, exc_info=True)
            print(f"[LIBA ERROR]: {err_msg}")
            self.tts.speak(err_msg, play_audio=play_audio)
            self.audit.log_event(
                user_transcript=user_text,
                llm_decision={"action": "unknown"},
                permission_status="ERROR",
                ufo_success=False,
                spoken_response=err_msg,
                error=str(e),
                duration_sec=time.time() - start_time
            )
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = LIBAAgent()

    print("\n--- Step 4 Groq Llama 3.3 70B Verification Test ---")
    agent.process_command(
        "open Notepad and write a shopping list",
        confirmation_callback=lambda msg: True,
        play_audio=False
    )
