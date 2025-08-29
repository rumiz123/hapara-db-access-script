#!/usr/bin/env python3
# hapara_objectid_investigator.py

import requests
import json
import sys
from typing import Dict, Any

# Your specific ObjectID
TARGET_OBJECT_ID = "b80ede03c926427d174500af9525d28c"


def get_latest_token() -> str:
    """Get the latest access token"""
    with open("../auth_token.jsonl", 'r') as f:
        return json.loads(f.readlines()[-1])["access_token"]


def investigate_object_id_endpoints(token: str, object_id: str):
    """Investigate endpoints that might work with this ObjectID"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    endpoints_to_test = [
        # Student-specific endpoints
        f"/hldata/student/{object_id}",
        f"/api/student/{object_id}",
        f"/v1/students/{object_id}",

        # Activity endpoints
        f"/hldata/student/{object_id}/activity",
        f"/api/student/{object_id}/activity",
        f"/v1/students/{object_id}/activity",

        # Screenshot endpoints
        f"/hldata/student/{object_id}/screenshots",
        f"/api/student/{object_id}/screenshots",
        f"/v1/students/{object_id}/screenshots",

        # Snapshots endpoints
        f"/hldata/student/{object_id}/snapshots",
        f"/api/student/{object_id}/snapshots",
        f"/v1/students/{object_id}/snapshots",

        # Timeline endpoints
        f"/hldata/student/{object_id}/timeline",
        f"/api/student/{object_id}/timeline",

        # Query parameter endpoints
        f"/hldata/activity?student_id={object_id}",
        f"/api/activity?studentId={object_id}",
        f"/v1/activity?student_id={object_id}",
        f"/hldata/snapshots?objectId={object_id}",
        f"/api/snapshots?objectId={object_id}",
    ]

    print(f"🔍 Investigating endpoints for ObjectID: {object_id}\n")

    results = {}

    for endpoint in endpoints_to_test:
        url = f"https://api.hapara.com{endpoint}"
        print(f"Testing: {url}")

        try:
            # Try GET first
            response = requests.get(url, headers=headers, timeout=10)

            result = {
                "get_status": response.status_code,
                "get_method": "GET"
            }

            if response.status_code == 200:
                try:
                    data = response.json()
                    result["get_data"] = data
                    print(f"✅ GET SUCCESS! Found data")
                    if isinstance(data, list):
                        print(f"   Items: {len(data)}")
                    elif isinstance(data, dict):
                        print(f"   Keys: {list(data.keys())[:10]}")
                except:
                    result["get_text"] = response.text[:200]
                    print(f"✅ GET SUCCESS! Text response")
            elif response.status_code == 404:
                print(f"❌ GET Not found")
            else:
                print(f"⚠️  GET Status: {response.status_code}")

            # Try POST if GET didn't work
            if response.status_code != 200:
                response_post = requests.post(url, headers=headers, json={"id": object_id}, timeout=10)
                result["post_status"] = response_post.status_code
                result["post_method"] = "POST"

                if response_post.status_code == 200:
                    try:
                        data = response_post.json()
                        result["post_data"] = data
                        print(f"✅ POST SUCCESS! Found data")
                    except:
                        result["post_text"] = response_post.text[:200]
                        print(f"✅ POST SUCCESS! Text response")
                else:
                    print(f"❌ POST Status: {response_post.status_code}")

            results[endpoint] = result

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results[endpoint] = {"error": str(e)}

        print("-" * 60)

    return results


def check_admin_for_object_id(token: str, object_id: str):
    """Check admin endpoints for this ObjectID"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    admin_payloads = [
        {"id": object_id},
        {"objectId": object_id},
        {"student_id": object_id},
        {"object_id": object_id},
        {"query": {"id": object_id}},
        {"filter": {"objectId": object_id}},
    ]

    admin_endpoints = [
        "/admin/config/student",
        "/admin/student/info",
        "/api/admin/student",
        "/v1/admin/students",
        "/admin/student/activity",
        "/admin/student/snapshots"
    ]

    print("🔍 Checking admin endpoints...\n")

    results = {}

    for endpoint in admin_endpoints:
        url = f"https://api.hapara.com{endpoint}"

        for i, payload in enumerate(admin_payloads):
            print(f"Testing: {url} with payload {i + 1}")

            try:
                response = requests.post(url, headers=headers, json=payload, timeout=10)

                result_key = f"{endpoint}_payload{i + 1}"
                results[result_key] = {
                    "status": response.status_code,
                    "payload": list(payload.keys())[0] if payload else "empty"
                }

                if response.status_code == 200:
                    try:
                        data = response.json()
                        results[result_key]["data"] = data
                        print(f"✅ SUCCESS! Found data")
                    except:
                        results[result_key]["text"] = response.text[:200]
                        print(f"✅ SUCCESS! Text response")
                else:
                    print(f"❌ Status: {response.status_code}")

            except Exception as e:
                print(f"❌ Error: {str(e)}")
                results[f"{endpoint}_payload{i + 1}"] = {"error": str(e)}

            print("-" * 40)

    return results


def main():
    print("[*] Hapara ObjectID Investigator")
    print(f"[*] Targeting ObjectID: {TARGET_OBJECT_ID}\n")

    try:
        token = get_latest_token()
        print(f"🔑 Token: {token[:20]}...")

        # Step 1: Investigate endpoints
        print("\n" + "=" * 80)
        print("STEP 1: ENDPOINT INVESTIGATION")
        print("=" * 80)
        endpoint_results = investigate_object_id_endpoints(token, TARGET_OBJECT_ID)

        # Step 2: Check admin endpoints
        print("\n" + "=" * 80)
        print("STEP 2: ADMIN ENDPOINTS")
        print("=" * 80)
        admin_results = check_admin_for_object_id(token, TARGET_OBJECT_ID)

        print("\n📊 Investigation complete!")

        # Save results
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"objectid_investigation_{TARGET_OBJECT_ID}_{timestamp}.json", 'w') as f:
            json.dump({
                "target_object_id": TARGET_OBJECT_ID,
                "endpoint_results": endpoint_results,
                "admin_results": admin_results
            }, f, indent=2)

        print(f"📁 Results saved to: objectid_investigation_{TARGET_OBJECT_ID}_{timestamp}.json")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()