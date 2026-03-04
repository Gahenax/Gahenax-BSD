"""Quick dispatch to Jules API for BSD Phase-2."""
import os, sys, json

try:
    import requests
except ImportError:
    print("pip install requests first")
    sys.exit(1)

API_BASE = "https://jules.googleapis.com/v1alpha"
API_KEY = os.environ.get("JULES_API_KEY", "")

if not API_KEY:
    print("ERROR: Set JULES_API_KEY env var")
    sys.exit(1)

headers = {
    "X-Goog-Api-Key": API_KEY,
    "Content-Type": "application/json",
}

prompt = (
    "Execute the BSD Phase-2 Parallel Falsifiability Sweep.\n\n"
    "### Pre-requisitos\n"
    "```bash\n"
    "pip install numpy sympy mpmath pytest\n"
    "PYTHONPATH=. pytest tests/test_bsd.py -v  # 27 must pass\n"
    "```\n\n"
    "### Comando principal\n"
    "```bash\n"
    "PYTHONPATH=. python jules_orders/jules_bsd_dispatch_p2_parallel.py\n"
    "```\n\n"
    "This runs 1,323 elliptic curves across 3 rank 5-7 seed families "
    "using 8 parallel workers.\n"
    "Parameters: prime_bound=5000, precision=35 dps, height_bound=30.\n\n"
    "### Entregables\n"
    "1. Run the script to completion\n"
    "2. Commit results in evidence/phase2/ with message: "
    "'jules: Phase-2 parallel sweep complete'\n"
    "3. Push to master\n\n"
    "### Output esperado\n"
    "- evidence/phase2/verdicts_phase2_parallel.jsonl\n"
    "- evidence/phase2/telemetry_phase2_parallel.jsonl\n"
    "- evidence/phase2/JULES_BSD_P2_PARALLEL_AGGREGATE.json\n"
)

payload = {
    "title": "[GAHENAX] BSD Phase-2: Rank 5-7 Parallel Falsifiability Sweep",
    "prompt": (
        "Clone https://github.com/Gahenax/Gahenax-BSD and execute the "
        "Phase-2 parallel falsifiability sweep.\n\n"
        "1. pip install numpy sympy mpmath pytest\n"
        "2. PYTHONPATH=. pytest tests/test_bsd.py -v (27 must pass)\n"
        "3. PYTHONPATH=. python jules_orders/jules_bsd_dispatch_p2_parallel.py\n\n"
        "This evaluates 1323 elliptic curves across rank 5-7 families "
        "using 8 parallel workers (prime_bound=5000, dps=35).\n\n"
        "When done, commit evidence/phase2/* with message: "
        "'jules: Phase-2 parallel sweep complete'\n\n"
        "Expected output files:\n"
        "- evidence/phase2/verdicts_phase2_parallel.jsonl\n"
        "- evidence/phase2/JULES_BSD_P2_PARALLEL_AGGREGATE.json"
    ),
}

print("=" * 55)
print(" JULES API DISPATCH — BSD Phase-2")
print("=" * 55)
print(f"API: {API_BASE}/sessions")
print(f"Repo: Gahenax/Gahenax-BSD")
print(f"Key: {API_KEY[:8]}...{API_KEY[-4:]}")
print()
print("Dispatching...", flush=True)

try:
    resp = requests.post(
        f"{API_BASE}/sessions",
        headers=headers,
        json=payload,
        timeout=30,
    )
    print(f"Status: {resp.status_code}")
    data = resp.json() if resp.ok else {}
    print(f"Response: {json.dumps(data, indent=2)[:800]}")

    if resp.ok:
        session_id = data.get("name", "unknown")
        print(f"\n[OK] Jules session created: {session_id}")

        # Save to dispatch log
        log_entry = {
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "order": "BSD_P2_PARALLEL",
            "session_id": session_id,
            "status": "DISPATCHED",
        }
        os.makedirs("jules_orders", exist_ok=True)
        with open("jules_orders/.dispatch_log.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        print(f"[LOG] Dispatch logged to jules_orders/.dispatch_log.jsonl")
    else:
        print(f"\n[ERROR] {resp.status_code}: {resp.text[:300]}")

except Exception as e:
    print(f"[ERROR] {e}")
