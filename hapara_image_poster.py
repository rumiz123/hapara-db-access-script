#!/usr/bin/env python3
# hapara_targeted_image_poster.py

import requests
import json
import sys
import base64
import os
from typing import Dict, Any
from datetime import datetime

# Configuration
API_BASE_URL = "https://api.hapara.com"
SNAPSHOTS_ENDPOINT = "/hldata/student/snapshots"
TOKENS_FILE = "auth_token.jsonl"

# Your specific ObjectID
TARGET_OBJECT_ID = "7703a9cc1f60ce65f9638cd66e509fb3"


def get_latest_token() -> str:
    """Get the latest access token"""
    with open(TOKENS_FILE, 'r') as f:
        return json.loads(f.readlines()[-1])["access_token"]


def image_to_base64(image_path: str) -> str:
    """Convert image to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def post_screenshot(token: str, object_id: str, image_data: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Post screenshot to Hapara API"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = f"{API_BASE_URL}{SNAPSHOTS_ENDPOINT}"

    payload = {
        "id": object_id,
        "image": image_data,
        "timestamp": datetime.now().isoformat() + "Z",
        "source": "targeted_test",
        "test_id": f"test_{int(datetime.now().timestamp())}"
    }

    if metadata:
        payload.update(metadata)

    print(f"📤 Posting to: {url}")
    print(f"🎯 ObjectID: {object_id}")
    print(f"📊 Image size: {len(image_data)} characters")
    print(f"📋 Payload keys: {list(payload.keys())}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)

        result = {
            "status": response.status_code,
            "timestamp": datetime.now().isoformat(),
            "object_id": object_id
        }

        if response.status_code == 200:
            try:
                result["response"] = response.json()
                print("✅ SUCCESS! Screenshot posted!")
                print(f"Response: {json.dumps(result['response'], indent=2)}")
            except:
                result["text"] = response.text
                print(f"✅ SUCCESS! Response: {response.text}")
        else:
            try:
                result["error"] = response.json()
                print(f"❌ Error: {json.dumps(result['error'])}")
            except:
                result["error_text"] = response.text
                print(f"❌ Error text: {response.text}")

        return result

    except Exception as e:
        error_msg = f"Request failed: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}


def test_with_target_object_id(token: str):
    """Test with the specific target ObjectID"""
    # Small test image
    test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="

    print(f"🎯 Testing with target ObjectID: {TARGET_OBJECT_ID}")

    # Test 1: Basic image post
    print("\n" + "=" * 60)
    print("TEST 1: BASIC IMAGE POST")
    print("=" * 60)
    result1 = post_screenshot(token, TARGET_OBJECT_ID, test_image, {
        "test_type": "basic",
        "description": "Basic test image post"
    })

    # Test 2: With additional metadata
    print("\n" + "=" * 60)
    print("TEST 2: WITH METADATA")
    print("=" * 60)
    result2 = post_screenshot(token, TARGET_OBJECT_ID, test_image, {
        "test_type": "with_metadata",
        "description": "Test with additional metadata",
        "custom_field": "test_value_123",
        "resolution": "100x100",
        "quality": "high"
    })

    # Test 3: Different image format
    print("\n" + "=" * 60)
    print("TEST 3: DIFFERENT IMAGE")
    print("=" * 60)
    # Another small test image (different pattern)
    test_image_2 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mNgYGB4AAAECAEAbwiy2AAAAABJRU5ErkJggg=="
    result3 = post_screenshot(token, TARGET_OBJECT_ID, test_image_2, {
        "test_type": "different_image",
        "description": "Different test image pattern"
    })

    return {
        "test1_basic": result1,
        "test2_metadata": result2,
        "test3_different_image": result3
    }


def investigate_object_id(token: str, object_id: str):
    """Investigate this specific ObjectID"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print(f"\n🔍 Investigating ObjectID: {object_id}")

    # Check admin config for this ObjectID
    admin_url = f"{API_BASE_URL}/admin/config/highlights"
    admin_payload = {"emails": [f"test_{object_id}@example.com"]}  # Fake email to trigger lookup

    try:
        response = requests.post(admin_url, headers=headers, json=admin_payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                print("✅ Admin config found:")
                print(json.dumps(data, indent=2))
            else:
                print("❌ No admin config data returned")
        else:
            print(f"❌ Admin config status: {response.status_code}")
    except Exception as e:
        print(f"❌ Admin config error: {e}")


def main():
    print("[*] Hapara Targeted Image Poster")
    print(f"[*] Using specific ObjectID: {TARGET_OBJECT_ID}\n")

    try:
        token = get_latest_token()
        print(f"🔑 Token: {token[:20]}...")

        # First investigate this ObjectID
        investigate_object_id(token, TARGET_OBJECT_ID)

        # Then test image posting
        print("\n" + "=" * 80)
        print("POSTING TEST IMAGES")
        print("=" * 80)

        results = test_with_target_object_id(token)

        # Summary
        print(f"\n📊 TEST SUMMARY:")
        success_count = sum(1 for r in results.values() if r.get('status') == 200)
        print(f"Successful posts: {success_count}/{len(results)}")

        for test_name, result in results.items():
            status = "✅" if result.get('status') == 200 else "❌"
            print(f"{status} {test_name}: Status {result.get('status', 'N/A')}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()