#!/usr/bin/env python3
# convert_token.py

import json
import requests
import sys
from pathlib import Path
from datetime import datetime

# Configuration
CAPTURES_FILE = "captures.jsonl"
TOKENS_FILE = "tokens.jsonl"  # New file for storing tokens
API_URL = "https://api.hapara.com/auth-service/oauth/token?grant_type=refresh_token"
HEADERS = {
    'sec-ch-ua-platform': '"Windows"',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0',
    'accept': 'application/json, text/plain, */*',
    'sec-ch-ua': '"Not;A=Brand";v="99", "Microsoft Edge";v="139", "Chromium";v="139"',
    'content-type': 'application/json',
    'sec-ch-ua-mobile': '?0',
    'origin': 'https://app.hapara.com',
    'sec-fetch-site': 'same-site',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty',
    'referer': 'https://app.hapara.com/',
    'accept-encoding': 'gzip, deflate, br, zstd',
    'accept-language': 'en-US,en;q=0.9'
}


def save_token(token_data):
    """Save token data to tokens.jsonl"""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "expires_in": token_data.get("expires_in"),
        "token_type": token_data.get("token_type")
    }

    with open(TOKENS_FILE, 'a') as f:
        f.write(json.dumps(entry) + '\n')

    print(f"[+] Token saved to {TOKENS_FILE}")


def get_latest_token():
    """Extracts the latest Authorization header from captures.jsonl"""
    try:
        with open(CAPTURES_FILE, 'r') as f:
            lines = f.readlines()
            if not lines:
                raise ValueError("No entries found in captures.jsonl")

            # Get last entry
            last_entry = json.loads(lines[-1])

            # Find Authorization header
            for header, value in last_entry['request_headers']:
                if header.lower() == 'authorization':
                    return value

            raise ValueError("No Authorization header found in last entry")
    except FileNotFoundError:
        raise FileNotFoundError(f"Could not find {CAPTURES_FILE}")
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in captures.jsonl")


def refresh_token(auth_token):
    """Makes the refresh token request"""
    headers = HEADERS.copy()
    headers['authorization'] = auth_token
    headers['content-length'] = '21'

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            data='{}',
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Token refresh failed: {str(e)}")


def main():
    print("[*] Token Converter - JEWISH BYPASS")

    # Verify captures file exists
    if not Path(CAPTURES_FILE).exists():
        print(f"[!] Error: {CAPTURES_FILE} not found", file=sys.stderr)
        return 1

    try:
        # Step 1: Get latest token
        print("[*] Extracting latest token from captures...")
        auth_token = get_latest_token()
        print(f"[+] Found token: {auth_token[:20]}...")

        # Step 2: Refresh token
        print("[*] Making refresh token request...")
        tokens = refresh_token(auth_token)

        # Step 3: Save and display results
        print("\n[+] Token refresh successful!")
        save_token(tokens)
        print(json.dumps(tokens, indent=2))

        return 0

    except Exception as e:
        print(f"[!] Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())