import requests
import json
import os
import re

SESSION_FILE = "gleam_sessions.json"

def load_sessions():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    return {}

def save_sessions(sessions):
    with open(SESSION_FILE, "w") as f:
        json.dump(sessions, f, indent=2)

def get_csrf(session):
    r = session.get("https://gleam.io/", headers={
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    })
    return session.cookies.get("XSRF-TOKEN", "")

def get_headers(session, csrf, campaign_key):
    return {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "X-XSRF-TOKEN": csrf,
        "Origin": "https://gleam.io",
        "Referer": f"https://gleam.io/{campaign_key}/test",
    }

def send_code(session, csrf, email, campaign_key):
    r = session.post(
        "https://gleam.io/recover-contestant",
        json={"email": email, "campaign_key": campaign_key},
        headers=get_headers(session, csrf, campaign_key)
    )
    print(f"Send code status: {r.status_code} | {r.text[:100]}")
    return r.status_code in [200, 201]

def verify_code(session, csrf, email, code, campaign_key):
    r = session.patch(
        "https://gleam.io/claim-contestant",
        json={"email": email, "code": code, "campaign_key": campaign_key},
        headers=get_headers(session, csrf, campaign_key)
    )
    print(f"Verify status: {r.status_code} | {r.text[:200]}")
    return r.status_code in [200, 201], r

def main():
    sessions_data = load_sessions()

    print("\n╔══════════════════════════════╗")
    print("║      GLEAM LOGIN BOT         ║")
    print("╚══════════════════════════════╝")

    campaign_link = input("\nMasukkan link campaign Gleam: ").strip()
    match = re.search(r'gleam\.io/(\w+)', campaign_link)
    if not match:
        print("❌ Link tidak valid")
        return
    campaign_key = match.group(1)
    print(f"✅ Campaign: {campaign_key}")

    print("\nKetik 'done' untuk selesai\n")

    while True:
        email = input("Email: ").strip()
        if email.lower() == "done":
            break

        session = requests.Session()
        csrf = get_csrf(session)
        # Update XSRF dari cookies setelah get homepage
        csrf = session.cookies.get("XSRF-TOKEN", csrf)

        print(f"⏳ Kirim kode ke {email}...")
        ok = send_code(session, csrf, email, campaign_key)
        if not ok:
            print(f"❌ Gagal kirim kode ke {email}")
            continue

        # Update csrf setelah request
        csrf = session.cookies.get("XSRF-TOKEN", csrf)

        code = input("Masukkan kode dari email: ").strip()
        if not code:
            print("❌ Kode kosong, skip")
            continue

        success, resp = verify_code(session, csrf, email, code, campaign_key)

        # Update csrf lagi
        csrf = session.cookies.get("XSRF-TOKEN", csrf)

        if success:
            cookies = {k: v for k, v in session.cookies.items()}
            sessions_data[email] = {
                "cookies": cookies,
                "campaign_key": campaign_key
            }
            save_sessions(sessions_data)
            print(f"✅ Login berhasil: {email}\n")
        else:
            print(f"❌ Login gagal: {email}\n")

    print(f"\n✅ Total session: {len(sessions_data)}")
    print(f"Disimpan di: {SESSION_FILE}")

if __name__ == "__main__":
    main()
