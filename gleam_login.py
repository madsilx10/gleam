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

def make_headers(session, campaign_key):
    csrf = session.cookies.get("XSRF-TOKEN", "")
    return {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "X-XSRF-TOKEN": csrf,
        "Origin": "https://gleam.io",
        "Referer": f"https://gleam.io/{campaign_key}/",
    }

def init_session(campaign_key):
    session = requests.Session()
    session.get(f"https://gleam.io/{campaign_key}/", headers={
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    })
    return session

def create_contestant(session, email, name, campaign_key):
    """Step 1: Daftar dengan email + nama"""
    r = session.patch(
        f"https://gleam.io/{campaign_key}",
        json={
            "campaign_key": campaign_key,
            "additional_details": False,
            "contestant": {
                "firstname": "",
                "lastname": "",
                "name": name,
                "email": email
            }
        },
        headers=make_headers(session, campaign_key)
    )
    print(f"Create contestant: {r.status_code} | {r.text[:100]}")
    return r.status_code in [200, 201, 202]

def request_email_code(session, campaign_key):
    """Step 2: Request kode via email (no payload)"""
    r = session.patch(
        "https://gleam.io/claim-contestant",
        json=None,
        headers=make_headers(session, campaign_key)
    )
    print(f"Request code: {r.status_code} | {r.text[:100]}")
    return r.status_code in [200, 201, 202]

def verify_code(session, email, code, campaign_key):
    """Step 3: Verify kode dari email"""
    r = session.post(
        "https://gleam.io/recover-contestant",
        json={"campaign_key": campaign_key, "code": code, "email": email},
        headers=make_headers(session, campaign_key)
    )
    print(f"Verify code: {r.status_code} | {r.text[:200]}")
    return r.status_code in [200, 201]

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
    print(f"✅ Campaign: {campaign_key}\n")
    print("Ketik 'done' untuk selesai\n")

    while True:
        email = input("Email: ").strip()
        if email.lower() == "done":
            break

        name = input("Nama: ").strip()

        session = init_session(campaign_key)

        # Step 1: Create contestant
        print("⏳ Daftar akun...")
        ok = create_contestant(session, email, name, campaign_key)
        if not ok:
            print(f"❌ Gagal daftar: {email}\n")
            continue

        # Step 2: Request kode email
        print("⏳ Request kode email...")
        ok = request_email_code(session, campaign_key)
        if not ok:
            print(f"❌ Gagal request kode: {email}\n")
            continue

        # Step 3: Verify kode
        code = input("Masukkan kode dari email: ").strip()
        if not code:
            print("❌ Kode kosong, skip\n")
            continue

        success = verify_code(session, email, code, campaign_key)
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
