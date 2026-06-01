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
    r = session.get(
        f"https://gleam.io/{campaign_key}/",
        headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )
    csrf = session.cookies.get("XSRF-TOKEN", "")
    owner_token = session.cookies.get("owner_token", "")
    print(f"owner_token: {owner_token[:20] if owner_token else 'not found'}...")
    return session, csrf, owner_token

def make_headers(csrf, campaign_key, x_ref=None):
    h = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "X-Requested-With": "XMLHttpRequest",
        "X-XSRF-TOKEN": csrf,
        "X-Xsrf-Token": csrf,
        "X-Csrf-Token": csrf,
        "Origin": "https://gleam.io",
        "Referer": f"https://gleam.io/{campaign_key}/",
        "Sec-Ch-Ua": '"Mises";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    if x_ref:
        h["X-Ref"] = x_ref
    return h

def queue_contestant(session, csrf, email, name, campaign_key):
    """Step 1: Submit nama + email"""
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
        headers=make_headers(csrf, campaign_key)
    )
    new_csrf = session.cookies.get("XSRF-TOKEN", csrf)
    x_ref = session.cookies.get("owner_token", None)
    print(f"Queue contestant: {r.status_code} | {r.text[:300]}")
    print(f"Response headers: {dict(r.headers)}")
    print(f"X-Ref: {x_ref[:20] if x_ref else 'not found'}...")
    return r.status_code in [200, 201, 202], new_csrf, x_ref

def claim_contestant(session, csrf, campaign_key, x_ref=None):
    """Step 2: Pilih email sebagai metode login"""
    r = session.patch(
        "https://gleam.io/claim-contestant",
        headers={**make_headers(csrf, campaign_key, x_ref), "Content-Length": "0"},
    )
    new_csrf = session.cookies.get("XSRF-TOKEN", csrf)
    print(f"Claim contestant: {r.status_code} | {r.text[:100]}")
    return r.status_code in [200, 201, 202], new_csrf

def send_recovery_code(session, csrf, email, campaign_key, x_ref=None):
    """Step 3: Kirim kode ke email"""
    r = session.post(
        "https://gleam.io/contestant_recovery_codes",
        json={
            "contestant_recovery_code": {"email": email},
            "campaign_key": campaign_key
        },
        headers=make_headers(csrf, campaign_key, x_ref)
    )
    new_csrf = session.cookies.get("XSRF-TOKEN", csrf)
    print(f"Send recovery code: {r.status_code} | {r.text[:100]}")
    return r.status_code in [200, 201, 202], new_csrf

def recover_contestant(session, csrf, email, code, campaign_key, x_ref=None):
    """Step 4: Verify kode"""
    r = session.post(
        "https://gleam.io/recover-contestant",
        json={"campaign_key": campaign_key, "code": code, "email": email},
        headers=make_headers(csrf, campaign_key, x_ref)
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

    x_ref = input("Masukkan X-Ref (dari DevTools): ").strip()
    print(f"✅ X-Ref: {x_ref}\n")
    print("Ketik 'done' untuk selesai\n")

    while True:
        email = input("Email: ").strip()
        if email.lower() == "done":
            break

        name = input("Nama: ").strip()

        session, csrf, _ = init_session(campaign_key)

        # Step 1: Queue contestant
        print("⏳ Submit email + nama...")
        ok, csrf, _ = queue_contestant(session, csrf, email, name, campaign_key)
        if not ok:
            print(f"❌ Gagal queue: {email}\n")
            continue

        # Step 2: Claim contestant
        print("⏳ Pilih email...")
        ok, csrf = claim_contestant(session, csrf, campaign_key, x_ref)
        if not ok:
            print(f"❌ Gagal claim: {email}\n")
            continue

        # Step 3: Send recovery code
        print("⏳ Kirim kode ke email...")
        ok, csrf = send_recovery_code(session, csrf, email, campaign_key, x_ref)
        if not ok:
            print(f"❌ Gagal kirim kode: {email}\n")
            continue

        # Step 4: Input kode
        code = input("Kode dari email: ").strip()
        if not code:
            print("❌ Kode kosong\n")
            continue

        success = recover_contestant(session, csrf, email, code, campaign_key, x_ref)
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
