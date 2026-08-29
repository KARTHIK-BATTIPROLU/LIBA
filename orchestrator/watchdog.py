"""
orchestrator/watchdog.py

24/7 Supervisor and Watchdog for LIBA Desktop Pet.
Keeps both the LIBA Voice Agent (Python background service) and the
Liebe Desktop Pet (Electron shell) continuously running.

If either process crashes or closes, the watchdog automatically restarts it.
"""

import os
import sys
import time
import signal
import logging
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "watchdog.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("LIBA.Watchdog")

PYTHONW_EXE = str(PROJECT_ROOT / ".venv" / "Scripts" / "pythonw.exe")
PYTHON_EXE = str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe")
ELECTRON_EXE = str(PROJECT_ROOT / "desktop_pet" / "node_modules" / "electron" / "dist" / "electron.exe")
PET_DIR = str(PROJECT_ROOT / "desktop_pet")

# Choose pythonw if available, else python
EXE_TO_USE = PYTHONW_EXE if os.path.exists(PYTHONW_EXE) else PYTHON_EXE

running = True


def handle_shutdown(signum, frame):
    global running
    logger.info("Shutdown signal received (%s). Terminating supervisor...", signum)
    running = False


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


def start_liba_service():
    logger.info("Starting LIBA Voice Agent service...")
    cmd = [EXE_TO_USE, str(PROJECT_ROOT / "run_liba.py"), "--mode", "background"]
    return subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
    )


def start_desktop_pet():
    logger.info("Starting Liebe Desktop Pet...")
    cmd = [ELECTRON_EXE, "."]
    return subprocess.Popen(
        cmd,
        cwd=PET_DIR,
    )


def supervise():
    logger.info("==================================================")
    logger.info("   LIBA 24/7 Full-Time Supervisor Active          ")
    logger.info("==================================================")

    liba_proc = start_liba_service()
    time.sleep(4)  # Allow event bridge to bind before starting Electron
    pet_proc = start_desktop_pet()

    while running:
        try:
            # Check LIBA Voice Agent
            if liba_proc.poll() is not None:
                logger.warning(
                    "LIBA Voice Agent exited with code %s. Restarting in 3s...",
                    liba_proc.returncode,
                )
                time.sleep(3)
                liba_proc = start_liba_service()

            # Check Desktop Pet
            if pet_proc.poll() is not None:
                logger.warning(
                    "Desktop Pet exited with code %s. Restarting in 3s...",
                    pet_proc.returncode,
                )
                time.sleep(3)
                pet_proc = start_desktop_pet()

            time.sleep(5)
        except KeyboardInterrupt:
            break
        except Exception as exc:
            logger.error("Supervisor loop error: %s", exc)
            time.sleep(5)

    logger.info("Shutting down child processes...")
    for proc, name in [(liba_proc, "LIBA Voice Agent"), (pet_proc, "Desktop Pet")]:
        if proc and proc.poll() is None:
            logger.info("Terminating %s...", name)
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()

    logger.info("LIBA Supervisor stopped cleanly.")


if __name__ == "__main__":
    supervise()