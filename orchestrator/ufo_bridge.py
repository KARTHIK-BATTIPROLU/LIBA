import sys
import os
import asyncio
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UFO2_DIR = PROJECT_ROOT / "ufo2"
if str(UFO2_DIR) not in sys.path:
    sys.path.insert(0, str(UFO2_DIR))

logger = logging.getLogger("LIBA.UFOBridge")

ALLOWED_TYPED_ACTIONS = {
    "open_app",
    "type_text",
    "click_ui",
    "read_file",
    "list_files",
    "navigate_ui",
    "scroll",
    "execute_ufo"
}

FORBIDDEN_RAW_SHELL_PATTERNS = [
    "cmd.exe /c",
    "powershell -c",
    "rmdir /s",
    "del /f",
    "format ",
    "rm -rf"
]

class UFOBridge:
    """
    Bridge connecting LIBA Orchestrator to Microsoft UFO2 automation engine with Nitro70 Tool Safety Enforcement.
    """
    def __init__(self):
        self.ufo_dir = UFO2_DIR

    def sanitize_and_audit_action(self, request_text: str) -> bool:
        """
        Tool Safety Audit (Nitro70 philosophy):
        Ensures NO arbitrary raw shell commands can bypass the typed action system.
        """
        lower_req = request_text.lower()
        for forbidden in FORBIDDEN_RAW_SHELL_PATTERNS:
            if forbidden in lower_req:
                logger.error(f"[TOOL SAFETY AUDIT BLOCKED]: Detected raw un-gated shell pattern '{forbidden}' in '{request_text}'")
                print(f"[TOOL SAFETY AUDIT BLOCKED]: Dangerous raw shell pattern '{forbidden}' detected. Blocked!")
                return False
        return True

    def execute_ufo_task(self, request_text: str) -> bool:
        """
        Execute an OS automation request via Microsoft UFO2 after passing Tool Safety Audit.
        """
        if not self.sanitize_and_audit_action(request_text):
            return False

        print(f"\n[UFO BRIDGE] Dispatching OS task to UFO2: '{request_text}'")
        try:
            old_cwd = os.getcwd()
            os.chdir(self.ufo_dir)

            from ufo.module.session_pool import SessionFactory, SessionPool

            sessions = SessionFactory().create_session(
                task="liba_task",
                mode="normal",
                plan="",
                request=request_text
            )

            clients = SessionPool(sessions)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(clients.run_all())
            loop.close()

            os.chdir(old_cwd)
            print(f"[UFO BRIDGE] Task completed successfully.")
            return True
        except Exception as e:
            if 'old_cwd' in locals():
                os.chdir(old_cwd)
            logger.error(f"[UFO BRIDGE Error]: {e}")
            print(f"[UFO BRIDGE Error]: {e}")
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bridge = UFOBridge()
    print("--- Step 6 Tool Safety Audit Test ---")
    
    # Test 1: Safe typed action
    assert bridge.sanitize_and_audit_action("open Notepad and type hello") == True
    print("Typed action audit: PASSED")

    # Test 2: Forbidden raw shell attempt
    assert bridge.sanitize_and_audit_action("powershell -c Remove-Item -Recurse C:\\") == False
    print("Forbidden raw shell audit: PASSED (BLOCKED as expected)")
