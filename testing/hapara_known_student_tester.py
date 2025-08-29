#!/usr/bin/env python3
# hapara_known_student_tester.py

import requests
import json

# Known student email from earlier discovery
KNOWN_STUDENT_EMAIL = "rumnel567@fusdk12.net"


def get_latest_token() -> str:
    """Get the latest access token"""
    with open("../auth_token.jsonl", 'r') as f:
        return json.loads(f.readlines()[-1])["access_token"]


def get_student_object_id(token: str, email: str) -> str:
    """Get the actual ObjectID for a known student"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = "https://api.hapara.com/admin/config/highlights"
    payload = {"emails": [email]}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                student_data = data[0]
                object_id = student_data.get('ID')
                if object_id and len(object_id) == 24:
                    return object_id
                else:
                    print(f"❌ Invalid ObjectID format: {object_id}")
            else:
                print("❌ No student data returned")
        else:
            print(f"❌ Admin config status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

    return None


def test_image_posting(token: str, object_id: str, email: str):
    """Test posting image with the real ObjectID"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = "https://api.hapara.com/hldata/student/snapshots"

    # Test image
    test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="

    payload = {
        "id": object_id,
        "image": test_image,
        "format": "base64",
        "student_email": email,
        "test": True,
        "description": f"Test image for {email}"
    }

    print(f"📤 Posting image for: {email}")
    print(f"🎯 Using ObjectID: {object_id}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)

        if response.status_code == 200:
            print("✅ SUCCESS! Image posted successfully!")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"Error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    print("[*] Hapara Known Student Tester")
    print(f"[*] Testing with known student: {KNOWN_STUDENT_EMAIL}\n")

    try:
        token = get_latest_token()
        print(f"🔑 Token: {token[:20]}...")

        # Get the actual ObjectID
        print(f"🔍 Getting ObjectID for: {KNOWN_STUDENT_EMAIL}")
        object_id = get_student_object_id(token, KNOWN_STUDENT_EMAIL)

        if object_id:
            print(f"🎯 Found ObjectID: {object_id}")

            # Test image posting
            print("\n" + "=" * 60)
            print("TESTING IMAGE POSTING")
            print("=" * 60)
            success = test_image_posting(token, object_id, KNOWN_STUDENT_EMAIL)

            if success:
                print(f"\n🎉 SUCCESS! Images can be posted for {KNOWN_STUDENT_EMAIL}")
                print(f"ObjectID: {object_id}")
            else:
                print(f"\n❌ Failed to post image for {KNOWN_STUDENT_EMAIL}")

        else:
            print("❌ Could not find valid ObjectID for student")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
