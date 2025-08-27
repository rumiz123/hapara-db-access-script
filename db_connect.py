#!/usr/bin/env python3
# db_connect.py

import json
import asyncio
import websockets
import sys
import base64
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any

# Configuration
TOKENS_FILE = "auth_token.jsonl"
WS_URL = "wss://api.hapara.com/messaging/connection/websocket"
WS_PROTOCOL = "centrifuge-json"
TOKEN_REFRESH_BUFFER = 60  # Refresh token 60 seconds before expiration


class TokenManager:
    """Manage JWT tokens including decoding and refresh logic"""

    @staticmethod
    def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
        """Decode JWT token payload"""
        try:
            # Split JWT into parts
            parts = token.split('.')
            if len(parts) != 3:
                return None

            # Decode the payload (middle part)
            payload = parts[1]
            # Add padding if needed
            padding = len(payload) % 4
            if padding:
                payload += '=' * (4 - padding)

            payload_bytes = base64.urlsafe_b64decode(payload)
            return json.loads(payload_bytes.decode('utf-8'))
        except Exception as e:
            print(f"[!] Token decode error: {str(e)}")
            return None

    @staticmethod
    def get_token_expiration(token: str) -> Optional[float]:
        """Get expiration timestamp from token"""
        payload = TokenManager.decode_jwt(token)
        if payload and 'exp' in payload:
            return float(payload['exp'])
        return None

    @staticmethod
    def get_latest_token() -> str:
        """Get the latest access token from tokens.jsonl"""
        try:
            with open(TOKENS_FILE, 'r') as f:
                lines = f.readlines()
                if not lines:
                    raise ValueError("No tokens found in tokens.jsonl")

                # Get the most recent token entry
                latest_entry = json.loads(lines[-1])
                token = latest_entry.get("access_token")

                if not token:
                    raise ValueError("No access_token found in latest entry")

                return token
        except Exception as e:
            raise RuntimeError(f"Token error: {str(e)}")

    @staticmethod
    def is_token_expiring_soon(token: str, buffer_seconds: int = TOKEN_REFRESH_BUFFER) -> bool:
        """Check if token will expire within buffer period"""
        expiration = TokenManager.get_token_expiration(token)
        if not expiration:
            return True  # Assume expired if we can't decode

        current_time = time.time()
        return expiration - current_time <= buffer_seconds


class WebSocketManager:
    """Manage WebSocket connection with token refresh"""

    def __init__(self):
        self.ws = None
        self.current_token = None
        self.connection_id = 1
        self.is_connected = False

    async def connect(self, token: str):
        """Establish WebSocket connection with authentication"""
        try:
            self.current_token = token
            self.ws = await websockets.connect(
                WS_URL,
                subprotocols=[WS_PROTOCOL]
            )

            # Send authentication message
            auth_msg = json.dumps({"id": self.connection_id, "connect": {"token": token}})
            await self.ws.send(auth_msg)
            print(f"[*] Sent authentication: {auth_msg}")

            # Verify connection by waiting for response
            response = await asyncio.wait_for(self.ws.recv(), timeout=10)
            print(f"[*] Connection response: {response}")

            self.is_connected = True
            return True

        except Exception as e:
            print(f"[!] Connection error: {str(e)}", file=sys.stderr)
            self.is_connected = False
            return False

    async def refresh_connection(self):
        """Refresh connection with new token"""
        print("[*] Refreshing token and reconnecting...")

        if self.ws:
            try:
                await self.ws.close()
            except:
                pass

        new_token = TokenManager.get_latest_token()
        return await self.connect(new_token)

    async def send_new_token(self, token: str):
        """Send a new token to the existing connection"""
        try:
            # Send refresh message with new token
            refresh_msg = json.dumps({"id": self.connection_id, "refresh": {"token": token}})
            await self.ws.send(refresh_msg)
            print(f"[*] Sent new token refresh: {refresh_msg}")

            # Update current token
            self.current_token = token
            return True
        except Exception as e:
            print(f"[!] Error sending new token: {str(e)}", file=sys.stderr)
            return False

    async def close(self):
        """Close WebSocket connection"""
        if self.ws:
            await self.ws.close()
            self.is_connected = False


async def websocket_handler(ws_manager: WebSocketManager):
    """Handle WebSocket connection and messaging with token refresh"""
    try:
        # Start message receiver and sender tasks
        receive_task = asyncio.create_task(receive_messages(ws_manager))
        send_task = asyncio.create_task(send_commands(ws_manager))
        monitor_task = asyncio.create_task(monitor_token(ws_manager))

        await asyncio.gather(receive_task, send_task, monitor_task)

    except Exception as e:
        print(f"[!] WebSocket handler error: {str(e)}", file=sys.stderr)
        raise


async def receive_messages(ws_manager: WebSocketManager):
    """Handle incoming messages"""
    while ws_manager.is_connected:
        try:
            msg = await asyncio.wait_for(ws_manager.ws.recv(), timeout=60)
            print(f"\n[Received] {msg}")

            # Auto-respond to empty messages
            if msg == "{}":
                pong_msg = '{"pong":{}}'
                await ws_manager.ws.send(pong_msg)
                print(f"[Auto-Response] {pong_msg}")

        except asyncio.TimeoutError:
            print("\n[*] No messages received for 60 seconds, sending ping")
            try:
                await ws_manager.ws.ping()
            except:
                print("[!] Ping failed, connection may be lost")
                ws_manager.is_connected = False

        except websockets.exceptions.ConnectionClosed:
            print("[!] Connection closed unexpectedly")
            ws_manager.is_connected = False
            break


async def send_commands(ws_manager: WebSocketManager):
    """Handle user command input"""
    with ThreadPoolExecutor(1) as executor:
        while ws_manager.is_connected:
            try:
                # Get user input without blocking
                command = await asyncio.get_event_loop().run_in_executor(
                    executor, input, "\n[Enter command (or 'exit' to quit)]: "
                )

                if command.lower() == 'exit':
                    print("[*] Closing connection...")
                    await ws_manager.close()
                    return

                # Validate JSON input
                try:
                    json.loads(command)  # Validate it's proper JSON
                    if ws_manager.is_connected:
                        await ws_manager.ws.send(command)
                        print(f"[Sent] {command}")
                    else:
                        print("[!] Not connected, cannot send message")
                except json.JSONDecodeError:
                    print("[!] Invalid JSON format", file=sys.stderr)

            except (EOFError, KeyboardInterrupt):
                print("\n[*] Closing connection...")
                await ws_manager.close()
                return


async def monitor_token(ws_manager: WebSocketManager):
    """Monitor token expiration and refresh when needed"""
    while ws_manager.is_connected:
        try:
            await asyncio.sleep(10)  # Check every 10 seconds

            if not ws_manager.current_token:
                continue

            # Check if token is expiring soon (1 minute before expiration)
            if TokenManager.is_token_expiring_soon(ws_manager.current_token, TOKEN_REFRESH_BUFFER):
                print("[*] Token expiring soon, getting new token...")

                # Get the latest token from file
                new_token = TokenManager.get_latest_token()

                # Check if the new token is different from current one
                if new_token != ws_manager.current_token:
                    print("[*] New token available, sending refresh...")

                    # Try to send the new token to the existing connection
                    success = await ws_manager.send_new_token(new_token)

                    if not success:
                        print("[!] Failed to send new token, reconnecting...")
                        success = await ws_manager.refresh_connection()
                        if not success:
                            print("[!] Token refresh failed")
                            break
                    else:
                        # Verify the new token expiration
                        new_expiration = TokenManager.get_token_expiration(new_token)
                        if new_expiration:
                            from datetime import datetime
                            exp_str = datetime.fromtimestamp(new_expiration).strftime('%Y-%m-%d %H:%M:%S')
                            print(f"[*] New token expires at: {exp_str}")
                else:
                    print("[*] No new token available yet, will check again soon")

        except Exception as e:
            print(f"[!] Token monitor error: {str(e)}")
            break


def main():
    print("[*] Hapara WebSocket Connector - Jewish Mode")
    print("[*] Type commands in JSON format or 'exit' to quit\n")

    try:
        # Get the latest token
        print("[*] Reading latest token...")
        token = TokenManager.get_latest_token()
        if not token:
            raise ValueError("No valid token found")

        # Decode and display token info
        token_data = TokenManager.decode_jwt(token)
        if token_data:
            exp_time = token_data.get('exp')
            if exp_time:
                from datetime import datetime
                exp_str = datetime.fromtimestamp(exp_time).strftime('%Y-%m-%d %H:%M:%S')
                time_until_expiry = exp_time - time.time()
                print(f"[*] Token expires at: {exp_str}")
                print(f"[*] Time until expiry: {int(time_until_expiry)} seconds")

        print(f"[*] Using token: {token[:20]}...")

        # Create WebSocket manager
        ws_manager = WebSocketManager()

        # Initial connection
        success = asyncio.get_event_loop().run_until_complete(
            ws_manager.connect(token)
        )

        if not success:
            raise RuntimeError("Initial connection failed")

        # Run WebSocket handler
        asyncio.get_event_loop().run_until_complete(
            websocket_handler(ws_manager)
        )

        return 0

    except Exception as e:
        print(f"\n[!] Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())