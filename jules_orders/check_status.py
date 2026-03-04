import requests, json, os
k = os.environ["JULES_API_KEY"]
h = {"X-Goog-Api-Key": k}
sessions = [
    ("rank5_fermigier", "6058785188192542930"),
    ("rank6_dujella",   "1978868707027204903"),
    ("rank7_elkies",    "15160488109273747577"),
]
for name, sid in sessions:
    r = requests.get(f"https://jules.googleapis.com/v1alpha/sessions/{sid}", headers=h, timeout=10)
    d = r.json()
    state = d.get("state", "?")
    updated = d.get("updateTime", "?")[:19]
    print(f"{name:20s} | {state:15s} | updated: {updated}")
