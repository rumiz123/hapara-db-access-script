#!/usr/bin/env python3
# hapara_student_monitor.py

import requests
import json
import sys
import asyncio
import websockets
from typing import Dict, Any, List

# Configuration
API_BASE_URL = "https://api.hapara.com"
ADMIN_CONFIG_ENDPOINT = "/admin/config/highlights"
TOKENS_FILE = "auth_token.jsonl"


def get_latest_token() -> str:
    """Get the latest access token"""
    with open(TOKENS_FILE, 'r') as f:
        return json.loads(f.readlines()[-1])["access_token"]


def get_student_config(token: str, email: str) -> Dict[str, Any]:
    """Get student configuration from admin endpoint"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {"emails": [email]}

    response = requests.post(
        f"{API_BASE_URL}{ADMIN_CONFIG_ENDPOINT}",
        headers=headers,
        json=payload,
        timeout=15
    )

    if response.status_code == 200:
        data = response.json()
        return data[0] if data else {}
    return {}


async def connect_to_student_bus(websocket_url: str):
    """Connect to student's real-time WebSocket"""
    print(f"🚀 Connecting to student WebSocket: {websocket_url}")

    try:
        async with websockets.connect(websocket_url) as ws:
            print("✅ Connected to student real-time bus!")
            print("📡 Listening for student activity events...")

            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=300)
                    print(f"\n🎯 REAL-TIME EVENT:")
                    print(f"{'-' * 40}")

                    try:
                        data = json.loads(message)
                        print(json.dumps(data, indent=2))

                        # Check for interesting event types
                        event_type = data.get('type', '')
                        if 'screenshot' in event_type.lower():
                            print("📸 SCREENSHOT CAPTURED!")
                        elif 'focus' in event_type.lower():
                            print("🎯 STUDENT FOCUS CHANGE!")
                        elif 'browsing' in event_type.lower():
                            print("🌐 BROWSING ACTIVITY!")

                    except json.JSONDecodeError:
                        print(f"Raw message: {message[:200]}...")

                except asyncio.TimeoutError:
                    print("⏰ No events for 5 minutes...")

    except Exception as e:
        print(f"❌ WebSocket error: {e}")


def monitor_student_activity(email: str):
    """Monitor a student's activity"""
    token = get_latest_token()

    print(f"[*] Fetching configuration for: {email}")
    config = get_student_config(token, email)

    if not config:
        print("❌ No configuration found for student")
        return

    print("\n" + "=" * 60)
    print("🎯 STUDENT CONFIGURATION DISCOVERED")
    print("=" * 60)

    # Display key information
    print(f"📧 Email: {config.get('Email')}")
    print(f"🆔 Google ID: {config.get('ID')}")
    print(f"✅ Valid: {config.get('Valid')}")
    print(f"📋 Invalid Reason: {config.get('InvalidCode', 'N/A')}")

    print(f"\n🌐 WebSocket URL: {config.get('HLBusURL')}")
    print(f"📸 Screenshot URL: {config.get('ScreenshotBusURL')}")

    # Show monitoring schedule
    monitoring = config.get('MonitoringTime', {})
    if monitoring:
        print(f"\n⏰ Monitoring Schedule:")
        print(f"   Timezone: {monitoring.get('Timezone')}")
        print(f"   Hours: {monitoring.get('Start')} - {monitoring.get('End')}")
        print(f"   Weekend: Sat={monitoring.get('Saturday')}, Sun={monitoring.get('Sunday')}")

    # Show enabled features
    features = config.get('FeatureFlags', {})
    enabled_features = [k for k, v in features.items() if v]
    if enabled_features:
        print(f"\n✅ ENABLED FEATURES:")
        for feature in enabled_features:
            print(f"   • {feature}")

    # Try to connect to real-time WebSocket
    websocket_url = config.get('HLBusURL')
    if websocket_url and websocket_url.startswith('wss://'):
        print(f"\n[*] Attempting real-time connection...")
        asyncio.run(connect_to_student_bus(websocket_url))
    else:
        print("❌ No valid WebSocket URL found")


def check_multiple_students(emails: List[str]):
    """Check configuration for multiple students"""
    token = get_latest_token()

    print(f"[*] Checking {len(emails)} students...")

    payload = {"emails": emails}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        f"{API_BASE_URL}{ADMIN_CONFIG_ENDPOINT}",
        headers=headers,
        json=payload,
        timeout=15
    )

    if response.status_code == 200:
        students = response.json()
        for student in students:
            print(f"\n👤 {student.get('Email')}:")
            print(f"   Valid: {student.get('Valid')}")
            print(f"   Reason: {student.get('InvalidCode', 'N/A')}")
            if student.get('Valid'):
                print("   ✅ ACTIVE MONITORING")
            else:
                print("   ❌ NOT MONITORED")


def main():
    print("[*] Hapara Student Activity Monitor")

    if len(sys.argv) > 1:
        # Monitor specific student
        email = sys.argv[1]
        monitor_student_activity(email)
    else:
        # Interactive mode
        email = input("Enter student email: ").strip()
        if email:
            monitor_student_activity(email)
        else:
            print("❌ Email required")


if __name__ == "__main__":
    main()