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

def init_session(campaign_key):
    session = requests.Session()
    # Load halaman campaign dulu biar dapat cookies
    r = session.get(
        f"https://gleam.io/{campaign_key}/",
        headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )
    # Ambil CSRF token
    csrf_token = session.cookies.get("XSRF-TOKEN", "")
    print(f"CSRF token: {csrf_token[:30]}...")
    return session, csrf_token

def make_headers(csrf_token, campaign_key):
    return {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "X-XSRF-TOKEN": csrf_token,
        "Origin": "https://gleam.io",
        "Referer": f"https://gleam.io/{campaign_key}/test",
        "Sec-Ch-Ua": '"Mises";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

def queue_contestant(session, csrf_token, email, name, campaign_key):
    """PATCH queue-contestant - submit email + nama"""
    r = session.patch(
        f"https://gleam.io/queue-contestant/{campaign_key}",
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
        headers=make_headers(csrf_token, campaign_key)
    )
    # Update CSRF dari response cookies
    new_csrf = session.cookies.get("XSRF-TOKEN", csrf_token)
    print(f"Queue contestant: {r.status_code} | {r.text[:150]}")
    return r.status_code in [200, 201, 202], new_csrf

def claim_contestant(session, csrf_token, campaign_key):
    """PATCH claim-contestant - request kode email"""
    r = session.patch(
        "https://gleam.io/claim-contestant",
        headers={**make_headers(csrf_token, campaign_key), "Content-Length": "0"},
    )
    new_csrf = session.cookies.get("XSRF-TOKEN", csrf_token)
    print(f"Claim contestant: {r.status_code} | {r.text[:150]}")
    return r.status_code in [200, 201, 202], new_csrf

def recover_contestant(session, csrf_token, email, code, campaign_key):
    """POST recover-contestant - verify kode"""
    r = session.post(
        "https://gleam.io/recover-contestant",
        json={"campaign_key": campaign_key, "code": code, "email": email},
        headers=make_headers(csrf_token, campaign_key)
    )
    print(f"Recover contestant: {r.status_code} | {r.text[:200]}")
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

        # Init session & dapat CSRF
        session, csrf = init_session(campaign_key)

        # Step 1: Queue contestant
        print("⏳ Submit email + nama...")
        ok, csrf = queue_contestant(session, csrf, email, name, campaign_key)
        if not ok:
            print(f"❌ Gagal: {email}\n")
            continue

        # Step 2: Claim contestant (request kode)
        print("⏳ Request kode email...")
        ok, csrf = claim_contestant(session, csrf, campaign_key)
        if not ok:
            print(f"❌ Gagal request kode: {email}\n")
            continue

        # Step 3: Input kode + verify
        code = input("Kode dari email: ").strip()
        if not code:
            print("❌ Kode kosong, skip\n")
            continue

        success = recover_contestant(session, csrf, email, code, campaign_key)
        if success:
            cookies = {k: v for k, v in session.cookies.items()}
            sessions_data[email] = {"cookies": cookies, "campaign_key": campaign_key}
            save_sessions(sessions_data)
            print(f"✅ Login berhasil: {email}\n")
        else:
            print(f"❌ Login gagal: {email}\n")

    print(f"\n✅ Total session: {len(sessions_data)}")

if __name__ == "__main__":
    main()
