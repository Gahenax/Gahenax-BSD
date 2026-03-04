"""Dispatch 3 Jules sessions for Phase-3 (one per family)."""
import os, sys, json, requests

API_BASE = "https://jules.googleapis.com/v1alpha"
API_KEY = os.environ.get("JULES_API_KEY", "")
if not API_KEY:
    print("ERROR: Set JULES_API_KEY"); sys.exit(1)

HEADERS = {"X-Goog-Api-Key": API_KEY, "Content-Type": "application/json"}

FAMILIES = [
    ("rank5_fermigier", "Rank 5 Fermigier"),
    ("rank6_dujella",   "Rank 6 Dujella"),
    ("rank7_elkies",    "Rank 7 Elkies"),
]

sessions = []

for family, label in FAMILIES:
    prompt = (
        f"Clone https://github.com/Gahenax/Gahenax-BSD (branch: master) and execute:\n\n"
        f"```bash\n"
        f"pip install numpy sympy mpmath pytest\n"
        f"PYTHONPATH=. pytest tests/test_bsd.py -v\n"
        f"PYTHONPATH=. python jules_orders/jules_bsd_dispatch_p3_multi.py --family {family}\n"
        f"```\n\n"
        f"This sweeps the {label} family with 16 parallel workers, radius=100, step=3.\n"
        f"When done, commit evidence/phase3/* and push."
    )

    payload = {
        "title": f"[GAHENAX] BSD P3: {label} (16 workers)",
        "prompt": prompt,
    }

    print(f"Dispatching {family}...", end=" ", flush=True)
    try:
        r = requests.post(f"{API_BASE}/sessions", headers=HEADERS, json=payload, timeout=30)
        d = r.json()
        sid = d.get("id", "?")
        url = d.get("url", "?")
        print(f"OK — {sid}")
        sessions.append({"family": family, "id": sid, "url": url, "status": "DISPATCHED"})
    except Exception as e:
        print(f"ERROR: {e}")
        sessions.append({"family": family, "id": None, "error": str(e)})

# Log all sessions
os.makedirs("jules_orders", exist_ok=True)
with open("jules_orders/.dispatch_log.jsonl", "a") as f:
    for s in sessions:
        f.write(json.dumps({"task": "BSD_P3", **s}) + "\n")

print(f"\n{'='*55}")
print(f" 3 JULES SESSIONS DISPATCHED")
print(f"{'='*55}")
for s in sessions:
    print(f"  {s['family']:20s} → {s.get('url', 'ERROR')}")
print(f"\nSession IDs: {[s['id'] for s in sessions]}")
