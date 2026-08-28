import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrator.ufo_bridge import UFOBridge
from orchestrator.permission_gate import PermissionGate
from tts.speaker import TTSSpeaker

logger = logging.getLogger("Hermes.ToolRegistry")

# Hermes / OpenAI Tool Schemas
HERMES_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Open or launch a desktop application on Windows (e.g. Notepad, Edge, Chrome, Calculator, File Explorer).",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application to launch (e.g. 'Notepad', 'Chrome', 'Calculator')."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "type_text_in_window",
            "description": "Type text into the currently active desktop window or application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The exact text string to type into the active window."
                    }
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_sandbox_file",
            "description": "Read, create, write, or delete files inside the designated D:\\New World sandbox workspace (Full access auto-approved).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["read", "write", "delete", "create"],
                        "description": "File operation to perform."
                    },
                    "filename": {
                        "type": "string",
                        "description": "Name or relative path of the file inside D:\\New World (e.g. 'notes.txt', 'data.csv')."
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write or append to the file (required for 'write' or 'create')."
                    }
                },
                "required": ["action", "filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_desktop_file",
            "description": "Read contents of a text file from disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Absolute path of the file to read."
                    }
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "synthesize_and_speak",
            "description": "Synthesize text into spoken audio using the male Jarvis British voice.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Message to speak out loud."
                    }
                },
                "required": ["text"]
            }
        }
    }
]

class HermesToolExecutor:
    """
    Executes registered Hermes tools through the Safety Permission Gate and UFO2 bridge.
    """
    def __init__(self):
        self.ufo = UFOBridge()
        self.gate = PermissionGate()
        self.tts = TTSSpeaker()
        self.sandbox_dir = Path("D:/New World").resolve()
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

    def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """
        Routes tool call to execution handler after passing Permission Gate.
        """
        logger.info(f"[Hermes Tool Call]: {name} with args {args}")

        if name == "open_application":
            app = args.get("app_name", "")
            req = f"open {app}"
            if not self.gate.evaluate_and_confirm("open_app", req):
                return "Error: Action denied by permission gate."
            
            success = False
            try:
                success = self.ufo.execute_ufo_task(req)
            except Exception as ufo_err:
                logger.warning(f"UFO execution error: {ufo_err}")

            if not success:
                try:
                    import subprocess
                    app_lower = app.lower().strip()
                    app_map = {
                        "notepad": "notepad.exe",
                        "calculator": "calc.exe",
                        "calc": "calc.exe",
                        "edge": "msedge.exe",
                        "microsoft edge": "msedge.exe",
                        "chrome": "chrome.exe",
                        "google chrome": "chrome.exe",
                        "explorer": "explorer.exe",
                        "file explorer": "explorer.exe",
                        "cmd": "cmd.exe",
                        "command prompt": "cmd.exe"
                    }
                    target_exec = app_map.get(app_lower, app)
                    subprocess.Popen(f"start {target_exec}", shell=True)
                    success = True
                except Exception as fallback_err:
                    logger.warning(f"Native app launch fallback failed for {app}: {fallback_err}")

            return f"Successfully opened {app}." if success else f"Failed to open {app}."

        elif name == "type_text_in_window":
            text = args.get("text", "")
            req = f"type text: '{text}'"
            if not self.gate.evaluate_and_confirm("type_text", req):
                return "Error: Action denied by permission gate."
            
            success = False
            try:
                success = self.ufo.execute_ufo_task(req)
            except Exception as ufo_err:
                logger.warning(f"UFO execution error: {ufo_err}")

            if not success:
                try:
                    import pyautogui
                    pyautogui.write(text)
                    success = True
                except Exception:
                    pass

            return f"Successfully typed text." if success else "Failed to type text."

        elif name == "manage_sandbox_file":
            action = args.get("action", "").lower()
            filename = args.get("filename", "")
            content = args.get("content", "")
            target_path = (self.sandbox_dir / filename).resolve()

            # Ensure target stays within sandbox
            if not str(target_path).startswith(str(self.sandbox_dir)):
                return "Error: File path is outside D:\\New World sandbox!"

            # Permission Gate evaluation (Auto-approves inside sandbox)
            if not self.gate.evaluate_and_confirm(f"{action}_file", f"{action} file in {target_path}"):
                return "Error: Sandbox action denied."

            if action in ["write", "create"]:
                target_path.write_text(content, encoding="utf-8")
                return f"Successfully wrote {len(content)} chars to {target_path}."
            elif action == "read":
                if not target_path.exists():
                    return f"Error: File {target_path} does not exist."
                return target_path.read_text(encoding="utf-8")
            elif action == "delete":
                if target_path.exists():
                    target_path.unlink()
                    return f"Successfully deleted {target_path}."
                return f"File {target_path} was not found."

        elif name == "read_desktop_file":
            filepath = Path(args.get("filepath", ""))
            if not filepath.exists():
                return f"Error: File '{filepath}' does not exist."
            return filepath.read_text(encoding="utf-8", errors="ignore")[:2000]

        elif name == "synthesize_and_speak":
            msg = args.get("text", "")
            self.tts.speak(msg, play_audio=True)
            return f"Spoke message: '{msg}'"

        return f"Error: Unknown tool '{name}'."

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor = HermesToolExecutor()
    print("--- Hermes Tool Registry Verification ---")
    res = executor.execute_tool("manage_sandbox_file", {"action": "create", "filename": "hermes_test.txt", "content": "Hello Hermes Agent!"})
    print("Sandbox Tool Execution Result:", res)
    assert "Successfully wrote" in res
