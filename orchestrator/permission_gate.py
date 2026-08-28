import os
import logging
from pathlib import Path
from typing import Callable, Optional, Dict, Any

logger = logging.getLogger("LIBA.PermissionGate")

SANDBOX_DIR = Path("D:/New World").resolve()

SAFE_ACTIONS = {
    "open_app",
    "click",
    "type_text",
    "read_file",
    "list_files",
    "navigate_ui",
    "scroll",
    "get_status",
    "search_web"
}

GATED_ACTIONS = {
    "delete_file",
    "delete_directory",
    "send_email",
    "send_message",
    "make_payment",
    "change_system_setting",
    "install_software",
    "run_terminal_command",
    "system_shutdown"
}

class PermissionGate:
    """
    LIBA Safety Gate enforcing full file access in D:\\New World sandbox
    while requiring explicit confirmation for destructive actions elsewhere.
    """
    def __init__(self, sandbox_dir: Path = SANDBOX_DIR):
        self.sandbox_dir = sandbox_dir
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.safe_actions = SAFE_ACTIONS
        self.gated_actions = GATED_ACTIONS

    def is_target_in_sandbox(self, description: str, action_params: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if the target path or description is within D:\\New World sandbox.
        """
        text = (description + " " + str(action_params or "")).lower()
        sandbox_str = str(self.sandbox_dir).lower()
        alt_sandbox_str = sandbox_str.replace("\\", "/")
        
        return (sandbox_str in text) or (alt_sandbox_str in text) or ("new world" in text)

    def is_gated(self, action_name: str, description: str = "", action_params: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determine if an action is gated.
        Actions inside D:\\New World sandbox are auto-approved as SAFE.
        """
        # Rule 1: Actions inside D:\New World sandbox have full access (Auto-Approved)
        if self.is_target_in_sandbox(description, action_params):
            logger.info(f"[PERMISSION GATE] Target is within sandbox '{self.sandbox_dir}' -> Auto-approved as SAFE.")
            return False

        action = action_name.lower()
        if action in self.safe_actions:
            return False

        if action in self.gated_actions:
            return True

        danger_keywords = ["delete", "remove", "pay", "buy", "send", "mail", "shutdown", "format", "wipe", "uninstall"]
        for kw in danger_keywords:
            if kw in action or kw in description.lower():
                return True

        return True

    def evaluate_and_confirm(
        self,
        action_name: str,
        description: str,
        confirmation_input_fn: Optional[Callable[[str], bool]] = None
    ) -> bool:
        """
        Evaluates action. Safe or sandbox actions auto-approve. Gated actions request user confirmation.
        """
        if not self.is_gated(action_name, description=description):
            print(f"[PERMISSION GATE] Action '{action_name}' is SAFE / Sandbox Scoped -> Auto-approved.")
            return True

        prompt_msg = f"[PERMISSION GATE WARNING] Action '{action_name}' is GATED ({description}). Approval required."
        print(f"\n{prompt_msg}")

        if confirmation_input_fn:
            approved = confirmation_input_fn(description)
        else:
            user_resp = input("Type 'yes' to approve action, or any other key to cancel: ").strip().lower()
            approved = user_resp == "yes"

        if approved:
            print(f"[PERMISSION GATE] Action '{action_name}' APPROVED by user.")
        else:
            print(f"[PERMISSION GATE] Action '{action_name}' DENIED by user.")

        return approved

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gate = PermissionGate()
    print("--- Permission Gate & Sandbox Rule Test ---")

    # Test 1: Delete file INSIDE D:\New World (Sandbox -> Auto-approved)
    res_sandbox = gate.evaluate_and_confirm("delete_file", "delete temporary log in D:\\New World\\temp.log")
    print(f"Sandbox Delete Result: Approved={res_sandbox}")
    assert res_sandbox == True

    # Test 2: Delete file OUTSIDE D:\New World (Outside -> Gated)
    res_outside = gate.evaluate_and_confirm(
        "delete_file", 
        "delete system document C:\\Important.txt",
        confirmation_input_fn=lambda msg: False
    )
    print(f"Outside Sandbox Delete Result: Approved={res_outside}")
    assert res_outside == False
