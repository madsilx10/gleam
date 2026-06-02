import requests
import json
import os
import re
import hashlib
import time

SESSION_FILE = "gleam_sessions.json"

def load_sessions():
    if not os.path.exists(SESSION_FILE):
        print("❌ gleam_sessions.json tidak ditemukan")
        return {}
    with open(SESSION_FILE, "r") as f:
        return json.load(f)

def load_file(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def gleam_md5(text):
    return hashlib.md5(text.encode()).hexdigest()

def generate_hash(em_id, em_type, details, campaign_key):
    """
    Hash formula: md5("-{cid}-{em_id}-{em_type}-{key}") with word-swap
    """
    key = details if details else ""
    raw = f"-{campaign_key}-{em_id}-{em_type}-{key}"
    return gleam_md5(raw)

def make_headers(cookies, xsrf, x_ref, campaign_key):
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    return {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "X-XSRF-TOKEN": xsrf,
        "X-Xsrf-Token": xsrf,
        "X-Csrf-Token": xsrf,
        "X-Ref": x_ref,
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://gleam.io",
        "Referer": f"https://gleam.io/{campaign_key}/",
        "Sec-Ch-Ua": '"Mises";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Cookie": cookie_str,
    }

def get_entry_methods(campaign_key, cookies, xsrf, x_ref):
    """Fetch entry methods dari HTML halaman campaign pakai curl_cffi"""
    from curl_cffi import requests as curl_req
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    r = curl_req.get(
        f"https://gleam.io/{campaign_key}/test",
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cookie": cookie_str,
        },
        impersonate="chrome110"
    )
    print(f"Get page: {r.status_code} | len={len(r.text)}")
    print(f"HTML preview: {r.text[:500]}")
    if r.status_code not in [200, 403]:
        return []

    match = re.search(r'"entry_methods"\s*:\s*(\[.*?\])\s*[,}]', r.text, re.DOTALL)
    if not match:
        match = re.search(r'entry_methods["\s:]+(\[.+?\])', r.text, re.DOTALL)

    if match:
        try:
            entry_methods = json.loads(match.group(1))
            return entry_methods
        except Exception as e:
            print(f"Parse error: {e}")

    print("⚠️ Tidak bisa parse entry methods")
    return []

def complete_quest(campaign_key, em_id, em_type, details, cookies, xsrf, x_ref, fraud_token):
    """Complete quest via PATCH queue-entry + GET access-entry"""
    h = generate_hash(em_id, em_type, details, campaign_key)

    payload = {
        "details": details if details else {},
        "h": h,
        "f": fraud_token,
        "use_hcaptcha": False,
        "use_turnstile": True,
        "challenge_response": None,
        "dbg": {
            "eds": {str(em_id): details if details else {}},
            "afd": {},
            "efd": {},
            "dtc": {},
            "car": True
        },
        "dbge": {
            "eed": "7",
            "hedr": f"5#{em_id}:{'undefined' if not details else details}",
            "csefr": "r[object Object]",
            "csefn": "#undefined"
        },
        "stats": {"e": "nd", "m": 7, "c": 7, "k": 0, "ts": 10, "tm": 0, "ml": 0, "cl": 0, "kl": 0, "tsl": 0, "tml": 0, "i": 0}
    }

    # PATCH queue-entry
    r = requests.patch(
        f"https://gleam.io/queue-entry/{campaign_key}/{em_id}",
        json=payload,
        headers=make_headers(cookies, xsrf, x_ref, campaign_key)
    )

    if r.status_code not in [200, 201, 202]:
        return False, r.status_code

    # Update cookies dari response
    for cookie in r.cookies:
        cookies[cookie.name] = cookie.value
    new_xsrf = cookies.get("XSRF-TOKEN", xsrf)

    # Task-location dari response
    task_location = r.headers.get("task-location", "")
    if not task_location:
        return False, "no task-location"

    time.sleep(1)

    # GET access-entry
    em_id_from_loc = task_location.split("/")[-1]
    r2 = requests.get(
        f"https://gleam.io{task_location}",
        headers=make_headers(cookies, new_xsrf, x_ref, campaign_key)
    )

    return r2.status_code in [200, 201], r2.status_code

def main():
    sessions = load_sessions()
    links = load_file("links.txt")
    uids = load_file("uids.txt")

    if not sessions:
        return

    emails = list(sessions.keys())
    total = len(emails)

    print("\n╔══════════════════════════════╗")
    print("║      GLEAM QUEST BOT         ║")
    print("╠══════════════════════════════╣")
    print(f"║  Total akun: {total:<17}║")
    print("╚══════════════════════════════╝")

    campaign_link = input("\nMasukkan link campaign Gleam: ").strip()
    match = re.search(r'gleam\.io/(\w+)', campaign_link)
    if not match:
        print("❌ Link tidak valid")
        return
    campaign_key = match.group(1)
    print(f"✅ Campaign: {campaign_key}")

    print("\nPilih mode:")
    print("1. Jalanin semua akun")
    print("2. Pilih satu akun")
    print("3. From akun ke-N")
    choice = input("\nPilih (1/2/3): ").strip()

    if choice == "1":
        indices = list(range(total))
    elif choice == "2":
        idx = int(input(f"Pilih akun (1-{total}): ")) - 1
        indices = [idx]
    elif choice == "3":
        start = int(input(f"Mulai dari akun ke- (1-{total}): ")) - 1
        indices = list(range(start, total))
    else:
        print("Pilihan tidak valid")
        return

    for i in indices:
        email = emails[i]
        session_data = sessions[email]
        cookies = session_data.get("cookies", {})

        xsrf = cookies.get("XSRF-TOKEN", "")
        x_ref = cookies.get("owner_token", "")
        fraud_token = "b2e3c007b3e6955a43713b70cf400693.7f9483abfa0776f74818c33b8e55fef7"

        link = links[i] if i < len(links) else ""
        uid = uids[i] if i < len(uids) else ""

        print(f"\n{'='*50}")
        print(f"[Akun {i+1}] {email}")

        # Fetch entry methods
        entry_methods = get_entry_methods(campaign_key, cookies, xsrf, x_ref)
        print(f"[Akun {i+1}] {len(entry_methods)} quest ditemukan")

        for em in entry_methods:
            em_id = em.get("id")
            em_type = em.get("entry_type", "")
            em_name = em.get("name", "unknown")

            # Tentukan details berdasarkan tipe
            if "uid" in em_name.lower() or "id" in em_name.lower():
                details = uid
            elif "link" in em_name.lower() or "url" in em_name.lower() or "tweet" in em_name.lower():
                details = link
            else:
                details = None

            ok, status = complete_quest(campaign_key, em_id, em_type, details, cookies, xsrf, x_ref, fraud_token)
            print(f"[Akun {i+1}] {'✅' if ok else '❌'} {em_name} ({status})")
            time.sleep(2)

        print(f"[Akun {i+1}] ✅ Selesai!")

        if i != indices[-1]:
            print(f"\n⏳ Delay 10 detik...")
            time.sleep(10)

    print("\n✅ Semua akun selesai!")

if __name__ == "__main__":
    main()
