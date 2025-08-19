#!/usr/bin/env python3
# db_connect.py

import json
import asyncio
import websockets
import sys
from concurrent.futures import ThreadPoolExecutor

# Configuration
TOKENS_FILE = "tokens.jsonl"
WS_URL = "wss://api.hapara.com/messaging/connection/websocket"
WS_PROTOCOL = "centrifuge-json"

async def websocket_handler(token):
    """Handle WebSocket connection and messaging"""
    try:
        async with websockets.connect(
                WS_URL,
                subprotocols=[WS_PROTOCOL]
        ) as ws:
            # Send authentication message
            auth_msg = json.dumps({"id": 1, "connect": {"token": token}})
            await ws.send(auth_msg)
            print(f"[*] Sent authentication: {auth_msg}")

            # Start message receiver and sender tasks
            receive_task = asyncio.create_task(receive_messages(ws))
            send_task = asyncio.create_task(send_commands(ws))

            await asyncio.gather(receive_task, send_task)

    except Exception as e:
        print(f"[!] WebSocket error: {str(e)}", file=sys.stderr)
        raise

async def receive_messages(ws):
    """Handle incoming messages"""
    while True:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=60)
            print(f"\n[Received] {msg}")

            # Auto-respond to empty messages
            if msg == "{}":
                pong_msg = '{"pong":{}}'
                await ws.send(pong_msg)
                print(f"[Auto-Response] {pong_msg}")

        except asyncio.TimeoutError:
            print("\n[*] No messages received for 60 seconds, sending ping")
            await ws.ping()

async def send_commands(ws):
    """Handle user command input"""
    with ThreadPoolExecutor(1) as executor:
        while True:
            try:
                # Get user input without blocking
                command = await asyncio.get_event_loop().run_in_executor(
                    executor, input, "\n[Enter command (or 'exit' to quit)]: "
                )

                if command.lower() == 'exit':
                    print("[*] Closing connection...")
                    await ws.close()
                    return

                # Validate JSON input
                try:
                    json.loads(command)  # Validate it's proper JSON
                    await ws.send(command)
                    print(f"[Sent] {command}")
                except json.JSONDecodeError:
                    print("[!] Invalid JSON format", file=sys.stderr)

            except (EOFError, KeyboardInterrupt):
                print("\n[*] Closing connection...")
                await ws.close()
                return

def get_latest_token():
    """Get the latest access token from tokens.jsonl"""
    try:
        with open(TOKENS_FILE, 'r') as f:
            lines = f.readlines()
            if not lines:
                raise ValueError("No tokens found in tokens.jsonl")
            return json.loads(lines[-1]).get("access_token")
    except Exception as e:
        raise RuntimeError(f"Token error: {str(e)}")

def main():
    print("[*] Hapara WebSocket Connector - Jewish Mode")
    print("[*] Type commands in JSON format or 'exit' to quit\n")

    try:
        # Get the latest token
        print("[*] Reading latest token...")
        token = get_latest_token()
        if not token:
            raise ValueError("No valid token found")
        print(f"[*] Using token: {token[:20]}...")

        # Run WebSocket handler
        asyncio.get_event_loop().run_until_complete(
            websocket_handler(token)
        )
        return 0

    except Exception as e:
        print(f"\n[!] Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())