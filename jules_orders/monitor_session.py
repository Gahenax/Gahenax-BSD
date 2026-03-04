"""Background Jules session monitor. Polls every 60s, writes to log."""
import requests, json, os, time, sys

API_KEY = os.environ.get("JULES_API_KEY", "")
SESSION_ID = sys.argv[1] if len(sys.argv) > 1 else "6287184695470583838"
URL = f"https://jules.googleapis.com/v1alpha/sessions/{SESSION_ID}"
HEADERS = {"X-Goog-Api-Key": API_KEY}
LOG = f"evidence/phase2/jules_monitor_{SESSION_ID}.log"

os.makedirs(os.path.dirname(LOG), exist_ok=True)

with open(LOG, "a", encoding="utf-8") as f:
    while True:
        try:
            r = requests.get(URL, headers=HEADERS, timeout=15)
            d = r.json()
            state = d.get("state", "?")
            t = time.strftime("%Y-%m-%d %H:%M:%S")
            msg = f"[{t}] State: {state}"
            print(msg, flush=True)
            f.write(msg + "\n")
            f.flush()
            if state not in ("IN_PROGRESS", "STARTING"):
                f.write(json.dumps(d, indent=2) + "\n")
                f.flush()
                print(f"FINAL STATE: {state}")
                print(json.dumps(d, indent=2))
                break
        except Exception as e:
            print(f"[poll error] {e}", flush=True)
        time.sleep(60)
