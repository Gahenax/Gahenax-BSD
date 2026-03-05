"""
Dispatch script for Jules: Run BSD Amalgam Architecture on Rank 7 Elkies.

Uses the new Amalgam Architecture (SageMath + GMP + MPI) to attempt
Rank 7 evaluation with exact integer arithmetic instead of mpmath floats.
"""
import os
import sys
import json
import requests

API_BASE = "https://jules.googleapis.com/v1alpha"
API_KEY = os.environ.get("JULES_API_KEY", "")
if not API_KEY:
    print("ERROR: JULES_API_KEY not set."); sys.exit(1)

HEADERS = {"X-Goog-Api-Key": API_KEY, "Content-Type": "application/json"}

prompt = """Clone https://github.com/Gahenax/Gahenax-BSD (branch: master) and execute:

```bash
# Install system dependencies  
sudo apt-get update && sudo apt-get install -y openmpi-bin libopenmpi-dev

# Install Python dependencies (SageMath + MPI)
pip install numpy sympy mpmath sagemath mpi4py

# Test the Amalgam Architecture layers in isolation first
export PYTHONPATH=.
python src/amalgam/sage_engine.py
python src/amalgam/gmp_engine_stub.py

# If tests pass, run the full MPI Amalgam sweep for Rank 7
mpirun --allow-run-as-root -np 8 python jules_orders/mpi_bsd_dispatch.py \\
    --family rank7_elkies \\
    --radius 30 --step 10 \\
    --prime_bound 1000 \\
    --precision 30

# Commit evidence if successful
```

Key difference from previous attempts: This uses SageMath 2-Selmer descent (integer arithmetic)
instead of mpmath floating-point, which is what was causing OOM crashes.
Commit evidence/supercomputing/* and push when done.
"""

payload = {"title": "[GAHENAX] BSD P3: Rank 7 Elkies — Amalgam Architecture", "prompt": prompt}

try:
    r = requests.post(f"{API_BASE}/sessions", headers=HEADERS, json=payload, timeout=30)
    r.raise_for_status()
    d = r.json()
    print(f"OK — Session ID: {d.get('id')} — URL: {d.get('url')}")
    with open("jules_orders/.dispatch_log.jsonl", "a") as f:
        f.write(json.dumps({"task": "BSD_P3_RANK7_AMALGAM", "id": d.get("id"), "url": d.get("url")}) + "\n")
except Exception as e:
    print(f"FAILED: {e}")
