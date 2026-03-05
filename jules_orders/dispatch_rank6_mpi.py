"""Dispatch Rank 6 Dujella using the MPI Architecture on Jules."""
import os
import sys
import json
import requests

API_BASE = "https://jules.googleapis.com/v1alpha"
API_KEY = os.environ.get("JULES_API_KEY", "")
if not API_KEY:
    print("ERROR: JULES_API_KEY environment variable not set.")
    sys.exit(1)

HEADERS = {"X-Goog-Api-Key": API_KEY, "Content-Type": "application/json"}

prompt = """Clone https://github.com/Gahenax/Gahenax-BSD (branch: master) and execute:

```bash
# Install MPI system dependencies
sudo apt-get update && sudo apt-get install -y openmpi-bin libopenmpi-dev

# Install Python dependencies including mpi4py
pip install numpy sympy mpmath pytest mpi4py

# Run the MPI Orchestrator with 8 workers.
export PYTHONPATH=.
mpirun --allow-run-as-root -np 8 python jules_orders/mpi_bsd_dispatch.py --family rank6_dujella --radius 100 --step 5 --prime_bound 5000 --precision 30
```

This tests the new MPI orchestration architecture for Rank 6 with 8 concurrent workers.
Commit evidence/supercomputing/* and push when done.
"""

payload = {
    "title": "[GAHENAX] BSD P3: Rank 6 Dujella (8 MPI Workers)",
    "prompt": prompt
}

print("Dispatching Rank 6 (MPI / 8 Workers) to Jules...", flush=True)
try:
    r = requests.post(f"{API_BASE}/sessions", headers=HEADERS, json=payload, timeout=30)
    r.raise_for_status()
    d = r.json()
    print(f"OK — Session ID: {d.get('id')} — URL: {d.get('url')}")

    # Track session
    with open("jules_orders/.dispatch_log.jsonl", "a") as f:
        f.write(json.dumps({
            "task": "BSD_P3_RANK6_MPI", 
            "id": d.get("id"), 
            "url": d.get("url")
        }) + "\n")
except Exception as e:
    print(f"FAILED to dispatch: {e}")
    if 'r' in locals():
        print(r.text)
