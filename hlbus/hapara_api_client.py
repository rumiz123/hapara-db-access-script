#!/usr/bin/env python3
# hapara_simple_sender.py

import requests
import json
import sys
import base64
import os
import time
from typing import Dict, Any
from datetime import datetime

# Configuration
API_BASE_URL = "https://api.hapara.com"
SNAPSHOTS_ENDPOINT = "/hldata/student/snapshots"
TOKENS_FILE = "../auth_token.jsonl"


def get_latest_token() -> str:
    """Get the latest access token from tokens.jsonl"""
    try:
        with open(TOKENS_FILE, 'r') as f:
            lines = f.readlines()
            if not lines:
                raise ValueError("No tokens found in tokens.jsonl")

            latest_entry = json.loads(lines[-1])
            token = latest_entry.get("access_token")

            if not token:
                raise ValueError("No access_token found in latest entry")

            return token
    except Exception as e:
        raise RuntimeError(f"Token error: {str(e)}")


def image_to_base64(image_path: str) -> str:
    """Convert image file to base64 string"""
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string
    except Exception as e:
        raise RuntimeError(f"Error encoding image: {str(e)}")


def capture_screenshot() -> str:
    """Capture screenshot and return base64 string"""
    try:
        import pyautogui
        screenshot = pyautogui.screenshot()
        screenshot_path = f"screenshot_{int(time.time())}.png"
        screenshot.save(screenshot_path)
        print(f"[*] Screenshot saved: {screenshot_path}")
        return image_to_base64(screenshot_path)
    except ImportError:
        raise RuntimeError("pyautogui not installed. Install with: pip install pyautogui")


def send_snapshot_simple(token: str, image_data: str, student_id: str) -> Dict[str, Any]:
    """
    Send snapshot to Hapara API with minimal required fields
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = f"{API_BASE_URL}{SNAPSHOTS_ENDPOINT}"

    # Minimal payload - only what's required
    payload = {
        "id": student_id,
        "image": image_data
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            return {"status": "success", "response": response.json()}
        else:
            return {"status": "error", "code": response.status_code, "error": response.text}

    except Exception as e:
        return {"status": "error", "error": str(e)}


def main():
    print("[*] Hapara Simple Snapshot Sender")

    try:
        # Get token
        token = get_latest_token()
        print(f"[*] Token: {token[:20]}...")

        # Get student ID
        student_id = input("Student ObjectID: ").strip()
        if not student_id:
            print("[!] Student ID required")
            return 1

        # Image source
        print("\nImage source:")
        print("1. File")
        print("2. Screenshot (requires pyautogui)")

        choice = input("Choice (1-2): ").strip()

        if choice == "1":
            file_path = input("File path: ").strip()
            if not os.path.exists(file_path):
                print(f"[!] File not found: {file_path}")
                return 1
            image_data = image_to_base64(file_path)

        elif choice == "2":
            try:
                image_data = capture_screenshot()
            except Exception as e:
                print(f"[!] {str(e)}")
                return 1

        else:
            print("[!] Invalid choice")
            return 1

        # Send snapshot
        print(f"\n[*] Sending to student {student_id}...")
        result = send_snapshot_simple(token, image_data, student_id)

        if result["status"] == "success":
            print("✅ Success!")
            print(f"Response: {json.dumps(result['response'], indent=2)}")
        else:
            print("❌ Failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")

        return 0

    except Exception as e:
        print(f"\n[!] Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())