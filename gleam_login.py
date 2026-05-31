import requests
import json
import os

SESSION_FILE = "gleam_sessions.json"

def load_sessions():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    return {}

def save_sessions(sessions):
    with open(SESSION_FILE, "w") as f:
        json.dump(sessions, f, indent=2)

def get_csrf_token(session):
    """Ambil CSRF token dari Gleam"""
    r = session.get("https://gleam.io/", headers={
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    # Ambil XSRF-TOKEN dari cookie
    csrf = session.cookies.get("XSRF-TOKEN", "")
    return csrf

def request_login(email, name):
    """Request magic code ke email"""
    session = requests.Session()
    csrf = get_csrf_token(session)

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-XSRF-TOKEN": csrf,
        "Origin": "https://gleam.io",
        "Referer": "https://gleam.io/",
    }

    payload = {
        "email": email,
        "name": name,
        "auth_type": "email"
    }

    r = session.post(
        "https://gleam.io/users/sign_in",
        json=payload,
        headers=headers
    )

    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:200]}")
    return session, csrf

def verify_code(session, csrf, email, code):
    """Verifikasi kode dari email"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-XSRF-TOKEN": csrf,
        "Origin": "https://gleam.io",
        "Referer": "https://gleam.io/",
    }

    payload = {
        "email": email,
        "token": code
    }

    r = session.post(
        "https://gleam.io/users/sign_in/email/verify",
        json=payload,
        headers=headers
    )

    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:300]}")
    return r.status_code == 200

def main():
    sessions_data = load_sessions()

    print("\n╔══════════════════════════════╗")
    print("║      GLEAM LOGIN BOT         ║")
    print("╚══════════════════════════════╝")
    print("\nKetik 'done' untuk selesai\n")

    while True:
        email = input("Email: ").strip()
        if email.lower() == "done":
            break

        name = input("Nama (bebas): ").strip()

        print(f"\n⏳ Kirim kode ke {email}...")
        session, csrf = request_login(email, name)

        code = input("Masukkan kode dari email: ").strip()
        if not code:
            print("❌ Kode kosong, skip")
            continue

        success = verify_code(session, csrf, email, code)
        if success:
            # Simpen semua cookies
            cookies = dict(session.cookies)
            sessions_data[email] = {
                "cookies": cookies,
                "name": name
            }
            save_sessions(sessions_data)
            print(f"✅ Login berhasil: {email}")
        else:
            print(f"❌ Login gagal: {email}")

        print()

    print(f"\n✅ Total session tersimpan: {len(sessions_data)}")
    print(f"Disimpan di: {SESSION_FILE}")

if __name__ == "__main__":
    main()
