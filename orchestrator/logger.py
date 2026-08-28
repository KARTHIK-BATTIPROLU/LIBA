import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_LOG_PATH = LOG_DIR / "audit.jsonl"
SESSION_LOG_PATH = LOG_DIR / "session.log"

# Configure file and console logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(SESSION_LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("LIBA.Audit")

class AuditLogger:
    """
    Structured logger recording full transcript -> decision -> action -> result traces.
    """
    def __init__(self, log_path: Path = AUDIT_LOG_PATH):
        self.log_path = log_path

    def log_event(
        self,
        user_transcript: str,
        llm_decision: Dict[str, Any],
        permission_status: str,
        ufo_success: Optional[bool],
        spoken_response: str,
        error: Optional[str] = None,
        duration_sec: float = 0.0
    ):
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "transcript": user_transcript,
            "decision": llm_decision,
            "permission_status": permission_status,
            "ufo_success": ufo_success,
            "spoken_response": spoken_response,
            "error": error,
            "duration_sec": round(duration_sec, 2)
        }

        logger.info(f"AUDIT RECORD: {json.dumps(record)}")
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

if __name__ == "__main__":
    audit = AuditLogger()
    audit.log_event(
        user_transcript="test ambiguous command",
        llm_decision={"action": "none"},
        permission_status="SAFE",
        ufo_success=True,
        spoken_response="Testing audit logger."
    )
    print(f"Audit log written to: {AUDIT_LOG_PATH}")
