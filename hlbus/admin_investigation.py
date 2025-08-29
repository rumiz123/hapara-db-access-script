#!/usr/bin/env python3
# hapara_admin_investigator.py

import requests
import json
import sys
from typing import Dict, Any, List

# Configuration
API_BASE_URL = "https://api.hapara.com"
ADMIN_CONFIG_ENDPOINT = "/admin/config/highlights"
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


def send_admin_config_request(token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send POST request to admin config endpoint
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    url = f"{API_BASE_URL}{ADMIN_CONFIG_ENDPOINT}"

    print(f"[*] Sending to: {url}")
    print(f"[*] Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        result = {
            "status": response.status_code,
            "headers": dict(response.headers),
            "url": response.url
        }

        print(f"[*] Status: {response.status_code}")
        print(f"[*] Response time: {response.elapsed.total_seconds():.3f}s")

        if response.status_code == 200:
            try:
                data = response.json()
                result["data"] = data
                print(f"✅ SUCCESS! Response: {json.dumps(data, indent=2)}")
            except json.JSONDecodeError:
                result["text"] = response.text
                print(f"✅ SUCCESS! Text response: {response.text[:200]}...")
        else:
            try:
                error_data = response.json()
                result["error"] = error_data
                print(f"❌ Error: {json.dumps(error_data, indent=2)}")
            except json.JSONDecodeError:
                result["error_text"] = response.text
                print(f"❌ Error text: {response.text}")

        return result

    except Exception as e:
        error_msg = f"Request failed: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}


def test_different_payloads(token: str, base_payload: Dict[str, Any]):
    """Test different variations of the payload"""
    test_cases = [
        # Original payload
        {"name": "Original payload", "payload": base_payload},

        # Minimal payload
        {"name": "Minimal - just emails", "payload": {
            "emails": base_payload["emails"]
        }},

        # Just flags
        {"name": "Only flags", "payload": {
            "flags": base_payload["flags"]
        }},

        # Single email
        {"name": "Single email", "payload": {
            "emails": [base_payload["emails"][0]],
            "flags": base_payload["flags"]
        }},

        # Additional parameters
        {"name": "With additional params", "payload": {
            **base_payload,
            "includeDetails": True,
            "format": "full"
        }},

        # Query-style
        {"name": "Query style", "payload": {
            "query": {
                "emails": base_payload["emails"],
                "features": base_payload["flags"]
            }
        }}
    ]

    results = {}

    for test_case in test_cases:
        print(f"\n{'=' * 60}")
        print(f"[*] TEST: {test_case['name']}")
        print(f"{'=' * 60}")

        result = send_admin_config_request(token, test_case["payload"])
        results[test_case["name"]] = result

        # Small delay between requests
        import time
        time.sleep(1)

    return results


def investigate_feature_flags(token: str):
    """Investigate individual feature flags"""
    flags_to_test = [
        "HAP-6944-screenshot-interval_extension",
        "PERM-0000-Allow-EyesOnMe-Escape_extension",
        "PERM-0000-debug-logging_extension",
        "HAP-9651-take-over-blocking-request",
        "HAP-9942-breaking-pause-screen-on-chromebook",
        "HAP-11000-new-deledao-id",
        "HAP-10524-normalization",
        "PS-1075-token-refresh-before-expiry",
        "SUPPORT_001-throttle-extension-logging",
        "PS-1895-enable-auth-in-extension",
        "PS-1350-student-class-level-ui-enhancements",
        "HAP-12335-currently-not-browsing",
        "HAP-12335-mv3-force-reinit-tabs"
    ]

    print(f"\n[*] Testing individual feature flags...")

    results = {}

    for flag in flags_to_test:
        print(f"\n[*] Testing flag: {flag}")

        payload = {
            "emails": ["yizhi.fang@studentkipp.org"],
            "flags": [flag]
        }

        result = send_admin_config_request(token, payload)
        results[flag] = result

        time.sleep(0.5)

    return results


def try_different_admin_endpoints(token: str, payload: Dict[str, Any]):
    """Try different admin endpoints that might be related"""
    admin_endpoints = [
        "/admin/config/highlights"
    ]

    results = {}

    for endpoint in admin_endpoints:
        print(f"\n[*] Testing endpoint: {endpoint}")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url = f"{API_BASE_URL}{endpoint}"

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)

            result = {
                "status": response.status_code,
                "endpoint": endpoint
            }

            if response.status_code == 200:
                try:
                    result["data"] = response.json()
                    print(f"✅ Success! Status: {response.status_code}")
                except:
                    result["text"] = response.text
                    print(f"✅ Success! Status: {response.status_code}")
            else:
                print(f"❌ Status: {response.status_code}")

            results[endpoint] = result

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results[endpoint] = {"error": str(e)}

        time.sleep(0.5)

    return results


def main():
    print("[*] Hapara Admin Config Investigator")
    print("[*] Testing /admin/config/highlights endpoint\n")

    try:
        token = get_latest_token()
        print(f"[*] Using token: {token[:20]}...")

        # The payload you discovered
        base_payload = {
            "emails": ["yizhi.fang@studentkipp.org"],
            "flags": [
                "HAP-6944-screenshot-interval_extension",
                "PERM-0000-Allow-EyesOnMe-Escape_extension",
                "PERM-0000-debug-logging_extension",
                "HAP-9651-take-over-blocking-request",
                "HAP-9942-breaking-pause-screen-on-chromebook",
                "HAP-11000-new-deledao-id",
                "HAP-10524-normalization",
                "PS-1075-token-refresh-before-expiry",
                "SUPPORT_001-throttle-extension-logging",
                "PS-1895-enable-auth-in-extension",
                "PS-1350-student-class-level-ui-enhancements",
                "HAP-12335-currently-not-browsing",
                "HAP-12335-mv3-force-reinit-tabs"
            ]
        }

        # Step 1: Test the original payload
        print("\n" + "=" * 60)
        print("[*] STEP 1: TESTING ORIGINAL PAYLOAD")
        print("=" * 60)
        result1 = send_admin_config_request(token, base_payload)

        print("\n[*] complete!")

        # Save results
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"admin_config_results_{timestamp}.json"

        all_results = {
            "original_payload": result1,
        }

        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2)

        print(f"[*] Results saved to: {results_file}")

        return 0

    except Exception as e:
        print(f"\n[!] Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import time

    sys.exit(main())