#!/usr/bin/env python3
# enhanced_screenshot_monitor.py

import asyncio
import websockets
import json
import sys
from datetime import datetime


async def monitor_for_screenshot_posts(websocket_url: str):
    """Monitor for screenshot post events"""
    print(f"🎯 Monitoring for screenshot posts on: {websocket_url}")
    print("📡 Waiting for image upload events... (Ctrl+C to stop)\n")

    try:
        async with websockets.connect(websocket_url) as ws:
            print("✅ Connected to monitoring bus!")

            # Send subscription for screenshot events
            subscribe_msg = {
                "type": "subscribe",
                "channel": "screenshots",
                "event": "screenshot.upload"
            }
            await ws.send(json.dumps(subscribe_msg))
            print("📤 Subscribed to screenshot events")

            event_count = 0

            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=300)
                    event_count += 1

                    print(f"\n{'=' * 60}")
                    print(f"📨 EVENT #{event_count} - {datetime.now().isoformat()}")
                    print(f"{'=' * 60}")

                    try:
                        data = json.loads(message)

                        # Check for screenshot-related data
                        is_screenshot = any([
                            'screenshot' in str(data).lower(),
                            'image' in str(data).lower(),
                            'upload' in str(data).lower(),
                            'capture' in str(data).lower(),
                            data.get('type', '').lower().find('screen') != -1
                        ])

                        if is_screenshot:
                            print("🎯 SCREENSHOT EVENT DETECTED!")

                            # Look for key information
                            if 'student' in data:
                                print(f"👤 Student: {data.get('student', {}).get('id', 'unknown')}")

                            if 'timestamp' in data:
                                print(f"⏰ Time: {data.get('timestamp')}")

                            if 'size' in data or 'image' in data:
                                print("🖼️ Image data detected")

                            # Check for our test markers
                            if 'source' in data and 'python_test_script' in str(data['source']):
                                print("🔧 OUR TEST IMAGE DETECTED!")

                        else:
                            print("📊 Other monitoring event")
                            print(f"Type: {data.get('type', 'unknown')}")

                        # Show full data
                        print(json.dumps(data, indent=2))

                    except json.JSONDecodeError:
                        print("📝 Raw message (non-JSON):")
                        print(message[:500] + ("..." if len(message) > 500 else ""))

                    print(f"{'=' * 60}")

                except asyncio.TimeoutError:
                    print("⏰ No events for 5 minutes...")
                    # Send keep-alive
                    await ws.ping()

    except websockets.exceptions.ConnectionClosed:
        print("❌ Connection closed by server")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    print("[*] Enhanced Screenshot Monitor")
    print("[*] Specifically watching for image upload events\n")

    # Use the WebSocket URL we discovered
    websocket_url = "wss://hl.hapara.com/oxygen/watch/hl/student/"
    print(f"🌐 Monitoring: {websocket_url}")

    try:
        asyncio.run(monitor_for_screenshot_posts(websocket_url))
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")


if __name__ == "__main__":
    main()