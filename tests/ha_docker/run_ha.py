#!/usr/bin/env python3
"""
Launch or manage the Windy Home test instance of Home Assistant.

Usage:
    python run_ha.py              # Start HA (or restart if already running)
    python run_ha.py start        # Same as above
    python run_ha.py stop         # Stop and remove the container
    python run_ha.py restart      # Restart (picks up integration code changes)
    python run_ha.py reset        # Wipe all data and start fresh
    python run_ha.py logs         # Tail container logs
    python run_ha.py status       # Show container status
    python run_ha.py test         # Run automated tests against the running instance

After starting, open http://localhost:18123 in your browser.
First run: complete onboarding, then add the Windy Home integration
via Settings > Devices & Services > Add Integration > "Windy Home".

The integration code is live-mounted — edit files in custom_components/windy_home/,
then run `python run_ha.py restart` to pick up changes.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HA_URL = "http://localhost:18123"


def compose(*args: str, check: bool = False, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=SCRIPT_DIR,
        check=check,
        capture_output=capture,
        text=True,
    )


def wait_for_ha(timeout: int = 120) -> bool:
    import urllib.error
    import urllib.request

    print("Waiting for Home Assistant to start", end="", flush=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = urllib.request.urlopen(f"{HA_URL}/api/", timeout=3)
            if r.status == 200:
                print(" ready!")
                return True
        except (urllib.error.URLError, OSError):
            pass
        print(".", end="", flush=True)
        time.sleep(3)
    print(" timed out!")
    return False


def cmd_start():
    print("Starting Home Assistant...")
    compose("up", "-d")
    if wait_for_ha():
        print("""
╔══════════════════════════════════════════════════════════════╗
║  Home Assistant is running at: http://localhost:18123       ║
║                                                              ║
║  First time? Complete the onboarding wizard in the browser.  ║
║  Then: Settings > Devices & Services > Add Integration       ║
║        > Search "Windy Home"                                 ║
║                                                              ║
║  After editing integration code, run:                        ║
║    python run_ha.py restart                                  ║
║                                                              ║
║  To stop:  python run_ha.py stop                             ║
║  To reset: python run_ha.py reset                            ║
╚══════════════════════════════════════════════════════════════╝
""")
    else:
        print("HA did not start. Check logs with: python run_ha.py logs")
        sys.exit(1)


def cmd_stop():
    print("Stopping Home Assistant...")
    compose("down")
    print("Stopped.")


def cmd_restart():
    print("Restarting Home Assistant (picks up code changes)...")
    compose("restart")
    if wait_for_ha():
        print("Restarted. Open http://localhost:18123")
    else:
        print("HA did not come back. Check: python run_ha.py logs")


def cmd_reset():
    print("Wiping all data and starting fresh...")
    compose("down", "-v", "--remove-orphans")
    compose("up", "-d")
    if wait_for_ha():
        print("Fresh instance ready at http://localhost:18123")
        print("Complete onboarding again in the browser.")
    else:
        print("HA did not start. Check: python run_ha.py logs")


def cmd_logs():
    compose("logs", "-f", "--tail=100")


def cmd_status():
    compose("ps")


def cmd_test():
    """Run the automated Docker integration tests against the running instance."""
    # Check if HA is running
    result = compose("ps", "--format", "{{.Status}}", capture=True)
    if "Up" not in (result.stdout or ""):
        print("HA is not running. Starting it first...")
        cmd_start()

    print("\nRunning automated integration tests...\n")
    subprocess.run(
        [sys.executable, "-m", "pytest", os.path.join(SCRIPT_DIR, "test_ha_docker.py"), "-v", "-s", "--timeout=120"],
        cwd=os.path.join(SCRIPT_DIR, "..", ".."),
    )


COMMANDS = {
    "start": cmd_start,
    "stop": cmd_stop,
    "restart": cmd_restart,
    "reset": cmd_reset,
    "logs": cmd_logs,
    "status": cmd_status,
    "test": cmd_test,
}


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"
    if cmd in ("-h", "--help"):
        print(__doc__)
        return
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(COMMANDS)}")
        sys.exit(1)
    COMMANDS[cmd]()


if __name__ == "__main__":
    main()
