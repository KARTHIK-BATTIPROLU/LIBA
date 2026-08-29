import sys
import json
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from hermes.tool_registry import HERMES_TOOLS_SCHEMA, HermesToolExecutor
from stt.groq_stt import GroqSTT
from tts.speaker import TTSSpeaker
from orchestrator.logger import AuditLogger
from orchestrator.groq_pool import groq_chat, pool_status

# Event bridge — non-blocking, graceful fallback
try:
    from orchestrator.event_bridge import send_event
except ImportError:
    def send_event(evt): pass

load_dotenv(PROJECT_ROOT / ".env")
logger = logging.getLogger("Hermes.Agent")

HERMES_SYSTEM_PROMPT = """
You are Hermes Agent, an autonomous persistent AI voice assistant operating on a Windows desktop.
You have access to native desktop tools:
- open_application: Open Windows apps.
- type_text_in_window: Type text into active application windows.
- manage_sandbox_file: Read, write, create, or delete files in D:\\New World (Full access).
- read_desktop_file: Read files from disk.
- synthesize_and_speak: Speak audio back to the user.

Use the provided tools whenever an action or file operation is requested. Always give concise, helpful responses.
"""

class HermesVoiceAgent:
    """
    Hermes Agent runtime connecting LIBA tools into an autonomous function-calling pipeline.
    """
    def __init__(self):
        self.executor = HermesToolExecutor()
        self.stt = GroqSTT()
        self.tts = TTSSpeaker()
        self.audit = AuditLogger()
        self.models = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "groq/compound"]
        status = pool_status()
        logger.info(
            "Initialized Hermes Voice Agent runtime. "
            "Groq pool: %d key(s), active key #%d.",
            status["total_keys"], status["active_key_index"]
        )

    def run_agent_turn(self, user_text: str, play_audio: bool = True) -> str:
        """
        Runs one full Hermes Agent tool-calling conversation turn.
        """
        start_t = time.time()
        print(f"\n==================================================")
        print(f"[HERMES AGENT INPUT]: '{user_text}'")

        messages = [
            {"role": "system", "content": HERMES_SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ]

        active_model = self.models[0]
        try:
            # 1. First model call with tools — pool handles key rotation automatically
            response = None
            for model_cand in self.models:
                try:
                    response = groq_chat(
                        model=model_cand,
                        messages=messages,
                        tools=HERMES_TOOLS_SCHEMA,
                        tool_choice="auto",
                        temperature=0.1
                    )
                    active_model = model_cand
                    break
                except Exception as m_err:
                    logger.debug("Hermes model %s error: %s", model_cand, m_err)
                    continue

            if not response:
                raise RuntimeError("All Groq models failed to respond!")

            msg = response.choices[0].message

            # 2. Check if model invoked tool calls
            if msg.tool_calls:
                print(f"[HERMES LLM ({active_model})]: Selected {len(msg.tool_calls)} tool call(s)")
                messages.append(msg) # Append assistant message with tool calls

                send_event("executing")
                for tool_call in msg.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments or "{}")
                    print(f"[HERMES EXECUTING TOOL]: {fn_name}({fn_args})")
                    
                    tool_output = self.executor.execute_tool(fn_name, fn_args)
                    print(f"[HERMES TOOL RESULT]: {tool_output}")

                    # Append tool result message
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": fn_name,
                        "content": str(tool_output)
                    })

                # 3. Final model call to generate natural language response after tool execution
                final_res = groq_chat(
                    model=active_model,
                    messages=messages,
                    tools=HERMES_TOOLS_SCHEMA,
                    temperature=0.1
                )
                final_msg = final_res.choices[0].message
                final_text = (final_msg.content or "").strip()
                if not final_text:
                    final_text = "Task executed successfully."
            else:
                final_text = (msg.content or "").strip()

            print(f"[HERMES AGENT RESPONSE]: '{final_text}'")
            if play_audio:
                send_event("speaking")
                self.tts.speak(final_text, play_audio=True)

            self.audit.log_event(
                user_transcript=user_text,
                llm_decision={"agent": "hermes", "model": active_model},
                permission_status="APPROVED",
                ufo_success=True,
                spoken_response=final_text,
                duration_sec=time.time() - start_t
            )
            return final_text

        except Exception as e:
            err_msg = f"Hermes Agent experienced an error: {e}"
            logger.error(err_msg, exc_info=True)
            print(f"[HERMES ERROR]: {err_msg}")
            if play_audio:
                self.tts.speak("Hermes Agent encountered an error executing that request.", play_audio=True)
            return err_msg

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = HermesVoiceAgent()
    print("\n--- Hermes Agent Tool Pipeline Verification Test ---")
    agent.run_agent_turn("Create a file named hermes_greeting.txt in D:\\New World with content 'Welcome to Hermes Agent!'", play_audio=False)
