# Chrome must be installed.

import json
import time
import hashlib
import re
import jwt
from datetime import datetime, timezone, timedelta
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------- Configuration ----------------------
APP_URL = "https://app.hapara.com/student"
TARGET_PREFIX = "https://api.hapara.com/auth-service/oauth/token"
WAIT_FOR_SIGNIN_SECONDS = 300
WAIT_FOR_TOKEN_SECONDS = 120
OUTPUT_FILE = "auth_token.jsonl"
AUTH_FILE = "auth.json"
DELAY_TIME = 1  # in seconds
TOKEN_EXPIRY_THRESHOLD = 300
CHECK_INTERVAL = 60
# -----------------------------------------------------------

def load_auth_credentials():
    try:
        with open(AUTH_FILE, 'r') as f:
            auth_data = json.load(f)
        return auth_data.get('email'), auth_data.get('password')
    except FileNotFoundError:
        print(f"Error: {AUTH_FILE} not found. Please create this file with your email and password.")
        print('Example format: {"email": "your@email.com", "password": "yourpassword"}')
        exit(1)
    except json.JSONDecodeError:
        print(f"Error: {AUTH_FILE} contains invalid JSON.")
        exit(1)


def build_driver(headless=False):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--start-maximized")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})  # enable CDP perf logs

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.setCacheDisabled", {"cacheDisabled": True})
    except Exception:
        pass

    return driver


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def get_matching_bodies(driver, target_prefix: str):
    matches = []
    logs = driver.get_log("performance")

    for entry in logs:
        try:
            msg = json.loads(entry["message"])["message"]
        except Exception:
            continue

        method = msg.get("method")
        params = msg.get("params", {})

        if method == "Network.responseReceived":
            resp = params.get("response", {})
            url = resp.get("url", "")
            req_id = params.get("requestId")
            if req_id and url.startswith(target_prefix):
                try:
                    body_obj = driver.execute_cdp_cmd(
                        "Network.getResponseBody",
                        {"requestId": req_id}
                    )
                    body_text = body_obj.get("body", "")
                    matches.append((url, body_text))
                except Exception:
                    # skip
                    pass

    return matches


def parse_access_token_from_json(body: str) -> str | None:
    # json
    try:
        obj = json.loads(body)
        if isinstance(obj, dict) and "access_token" in obj:
            return str(obj["access_token"])
    except Exception:
        pass

    # Fallback
    m = re.search(r'"access_token"\s*:\s*"([^"]+)"', body)
    if m:
        return m.group(1)
    return None


def decode_jwt_token(token: str):
    """Decode JWT token without verification to get expiration time"""
    try:
        # Decode without verification since we don't have the secret key
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except jwt.InvalidTokenError:
        print("Error: Invalid JWT token")
        return None


def get_token_expiry(token: str):
    """Get expiration time from JWT token"""
    decoded = decode_jwt_token(token)
    if decoded and 'exp' in decoded:
        return datetime.fromtimestamp(decoded['exp'], timezone.utc)
    return None


def is_token_expiring_soon(expiry_time):
    """Check if token is about to expire"""
    if not expiry_time:
        return True  # Assume expired if we can't determine

    time_until_expiry = expiry_time - datetime.now(timezone.utc)
    return time_until_expiry.total_seconds() < TOKEN_EXPIRY_THRESHOLD


def automate_google_login(driver, email, password):
    print("Starting automated Google login...")
    time.sleep(DELAY_TIME)
    try:
        google_iframe = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "L5Fo6c-PQbLGe"))
        )
        time.sleep(DELAY_TIME)
        google_iframe.click()
        print("Clicked Google Sign-in iframe")
    except Exception as e:
        print(f"Could not find Google Sign-in iframe by class name: {e}")
        try:
            google_iframe = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "iframe[title*='Sign in with Google']"))
            )
            time.sleep(DELAY_TIME)
            google_iframe.click()
            print("Clicked Google Sign-in iframe (found by title)")
        except Exception as e2:
            print(f"Could not find Google Sign-in iframe by title either: {e2}")
            return False

    time.sleep(DELAY_TIME)
    if len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[1])
        print("Switched to login tab")
    else:
        print("No new tab detected, continuing in current window")

    time.sleep(DELAY_TIME)

    try:
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        time.sleep(DELAY_TIME)
        email_field.clear()
        email_field.send_keys(email)
        print("Entered email")

        time.sleep(DELAY_TIME)

        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']"))
        )
        time.sleep(DELAY_TIME)
        next_button.click()
        print("Clicked Next button")
    except Exception as e:
        print(f"Error in email entry step: {e}")
        return False

    time.sleep(DELAY_TIME)

    try:
        second_email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "i0116"))
        )
        time.sleep(DELAY_TIME)
        second_email_field.clear()
        second_email_field.send_keys(email)
        print("Entered email in second field")

        time.sleep(DELAY_TIME)

        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "idSIButton9"))
        )
        time.sleep(DELAY_TIME)
        next_button.click()
        print("Clicked Next button on second screen")
    except Exception as e:
        print(f"Error in second email step: {e}")
        # Continue

    time.sleep(DELAY_TIME)

    # password
    try:
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "i0118"))
        )
        time.sleep(DELAY_TIME)
        password_field.clear()
        password_field.send_keys(password)
        print("Entered password")

        time.sleep(DELAY_TIME)

        signin_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "idSIButton9"))
        )
        time.sleep(DELAY_TIME)
        signin_button.click()
        print("Clicked Sign in button")
    except Exception as e:
        print(f"Error in password entry step: {e}")
        return False

    time.sleep(DELAY_TIME)

    try:
        yes_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input#idSIButton9[value='Yes']"))
        )
        time.sleep(DELAY_TIME)
        yes_button.click()
        print("Clicked 'Yes' button on stay signed in prompt")
    except Exception as e:
        print(f"Could not find 'Yes' button or it's not needed: {e}")

    time.sleep(DELAY_TIME)

    try:
        continue_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Continue']"))
        )
        time.sleep(DELAY_TIME)
        continue_button.click()
        print("Clicked 'Continue' button")
    except Exception as e:
        print(f"Could not find 'Continue' button or it's not needed: {e}")

    time.sleep(DELAY_TIME)

    if len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[0])
        print("Switched back to main tab")

    return True


def capture_token():
    """Capture a new token by performing the login process"""
    email, password = load_auth_credentials()
    if not email or not password:
        print("Error: Email or password not found in auth.json")
        return None, None

    driver = build_driver()
    token = None
    expiry = None

    try:
        print(f"Opening {APP_URL}")
        driver.get(APP_URL)
        time.sleep(DELAY_TIME)

        if automate_google_login(driver, email, password):
            print("Login process completed successfully")
        else:
            print("Login process failed")
            return None, None

        print("Watching for a response from:", TARGET_PREFIX)

        try:
            WebDriverWait(driver, WAIT_FOR_SIGNIN_SECONDS).until(
                lambda d: d.current_url != APP_URL
            )
            print("Detected navigation change; continuing to monitor network…")
        except Exception:
            print("Continuing anyway; monitoring network for token responses…")

        deadline = time.time() + WAIT_FOR_TOKEN_SECONDS
        found = False
        while time.time() < deadline and not found:
            time.sleep(DELAY_TIME)
            for url, body in get_matching_bodies(driver, TARGET_PREFIX):
                token = parse_access_token_from_json(body)
                if token:
                    expiry = get_token_expiry(token)
                    record = {
                        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "url": url,
                        "access_token": token,
                        "access_token_sha256": sha256_hex(token),
                        "expiry_time": expiry.isoformat() if expiry else "unknown",
                        "body_excerpt": (body[:200] + "...") if len(body) > 200 else body
                    }
                    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                        f.write(json.dumps(record) + "\n")
                    print(f"[OK] Token observed from {url}")
                    print(f"Token expires at: {expiry}")
                    found = True
                    break

        if not found:
            print("No token response detected within the wait window.")

    finally:
        driver.quit()

    return token, expiry


def main():
    # Initial token capture
    token, expiry = capture_token()

    if not token:
        print("Failed to capture initial token. Exiting.")
        return

    # Monitor token and refresh when needed
    while True:
        if is_token_expiring_soon(expiry):
            print("Token is expiring soon. Capturing new token...")
            token, expiry = capture_token()

            if not token:
                print("Failed to capture new token. Retrying in 1 minute.")
                time.sleep(60)
                continue
        else:
            # Calculate time until expiry
            time_until_expiry = (expiry - datetime.now(timezone.utc)).total_seconds()
            check_interval = min(CHECK_INTERVAL, max(30, time_until_expiry - TOKEN_EXPIRY_THRESHOLD - 10))

            print(f"Token still valid. Next check in {check_interval} seconds.")
            time.sleep(check_interval)


if __name__ == "__main__":
    main()