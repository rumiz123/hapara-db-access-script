#!/usr/bin/env python3
# start.py - Automated token capture, conversion, and WebSocket connection
# For sanctioned pentest use only!

import subprocess
import sys
import time
import threading
from pathlib import Path
import os

# Configuration
MITMDUMP_CMD = [
    "mitmdump",
    "-s", "get_token.py",
    "--set", "outfile=captures.jsonl",
    "--set", "capture_bodies=true"
]

CONVERT_SCRIPT = "convert_token.py"
DB_CONNECT_SCRIPT = "db_connect.py"
TARGET_URL = "https://api.hapara.com/auth-service/oauth/token?grant"
SHUTDOWN_DELAY = 5  # seconds after detection before shutdown


def prompt_proxy_enable():
    """Prompt user to enable proxy before starting"""
    print("\n[!] IMPORTANT: Please configure your system to use mitmproxy as its proxy now")
    print("[*] Typically this means:")
    print("    1. Set HTTP/HTTPS proxy to 127.0.0.1:8080")
    print("    2. Install mitmproxy's CA certificate if needed")
    print("[*] Press Enter when ready to begin capture...")
    input()


def clear_old_files():
    """Remove previous capture files if they exist"""
    files_to_clear = ['captures.jsonl', 'tokens.jsonl']
    for filename in files_to_clear:
        if Path(filename).exists():
            try:
                os.remove(filename)
                print(f"[*] Removed existing {filename}")
            except Exception as e:
                print(f"[!] Failed to remove {filename}: {str(e)}", file=sys.stderr)


class MitmMonitor:
    def __init__(self):
        self.detected = False
        self.process = None
        self.timer = None

    def check_output(self, line):
        """Check mitmdump output for target request"""
        if not self.detected and "POST" in line and TARGET_URL in line:
            print(f"\n[+] Target request detected: {TARGET_URL}")
            print(f"[*] Will shutdown mitmdump in {SHUTDOWN_DELAY} seconds...")
            self.detected = True
            self.start_shutdown_timer()

    def start_shutdown_timer(self):
        """Start timer to shutdown mitmdump"""
        self.timer = threading.Timer(SHUTDOWN_DELAY, self.shutdown_mitmdump)
        self.timer.start()

    def shutdown_mitmdump(self):
        """Gracefully shutdown mitmdump"""
        if self.process and self.process.poll() is None:
            print("[*] Shutting down mitmdump...")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()


def run_mitmdump(monitor):
    """Run mitmdump with monitoring"""
    print("[*] Starting mitmdump with token logger...")
    print(f"[*] Command: {' '.join(MITMDUMP_CMD)}")
    print(f"[*] Waiting for POST to {TARGET_URL}\n")

    try:
        monitor.process = subprocess.Popen(
            MITMDUMP_CMD,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Monitor output in real-time
        for line in monitor.process.stdout:
            print(line, end='')
            monitor.check_output(line)

        monitor.process.wait()
        return monitor.process.returncode

    except FileNotFoundError:
        print("[!] Error: mitmdump not found. Is it installed?", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[!] Error running mitmdump: {str(e)}", file=sys.stderr)
        return 1
    finally:
        if monitor.timer:
            monitor.timer.cancel()


def run_converter():
    """Run the token converter script"""
    if not Path(CONVERT_SCRIPT).exists():
        print(f"[!] Error: {CONVERT_SCRIPT} not found", file=sys.stderr)
        return 1

    print("\n[*] Running token converter...")
    try:
        result = subprocess.run(
            [sys.executable, CONVERT_SCRIPT],
            capture_output=True,
            text=True
        )

        # Print the output
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        return result.returncode

    except Exception as e:
        print(f"[!] Error running converter: {str(e)}", file=sys.stderr)
        return 1


def run_db_connect():
    """Run the database WebSocket connector"""
    if not Path(DB_CONNECT_SCRIPT).exists():
        print(f"[!] Error: {DB_CONNECT_SCRIPT} not found", file=sys.stderr)
        return 1

    print("\n[*] Starting WebSocket connection...")
    try:
        # Run in foreground to see WebSocket messages
        process = subprocess.Popen(
            [sys.executable, DB_CONNECT_SCRIPT],
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        return process.wait()
    except Exception as e:
        print(f"[!] Error running db_connect: {str(e)}", file=sys.stderr)
        return 1


def prompt_proxy_disable():
    """Prompt user to disable proxy and press enter"""
    print("\n[!] IMPORTANT: Please disable your proxy settings now")
    print("[*] Press Enter to continue with token conversion...")
    input()


def main():
    print("[*] Starting automated token capture and conversion")

    # Step 0: Ensure proxy is configured
    prompt_proxy_enable()

    # Clear any existing capture files
    clear_old_files()

    monitor = MitmMonitor()

    # Step 1: Run mitmdump with monitoring
    return_code = run_mitmdump(monitor)

    if return_code != 0 and not monitor.detected:
        print("[!] mitmdump exited with errors", file=sys.stderr)
        return return_code

    # Step 2: Prompt user to disable proxy
    if monitor.detected:
        prompt_proxy_disable()

        # Step 3: Run token converter
        convert_result = run_converter()
        if convert_result != 0:
            return convert_result

        # Step 4: Connect to WebSocket
        print("\n[*] Proceeding to WebSocket connection...")
        return run_db_connect()
    else:
        print("[!] Target request was not detected", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] Process interrupted by user", file=sys.stderr)
        sys.exit(1)