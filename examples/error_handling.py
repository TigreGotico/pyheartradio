"""Robust usage — timeouts, HTTP errors, and empty results.

Shows the exception types you need to handle when building production code
that calls the iHeartRadio API.

Run:
    python examples/error_handling.py
"""
import requests
from pyheartradio import IHeartRadio

# ── Timeout ───────────────────────────────────────────────────────────────
print("1. Custom timeout (2 s):")
client = IHeartRadio(timeout=2)
print(f"   client.timeout = {client.timeout}")

# ── HTTP error ────────────────────────────────────────────────────────────
print("\n2. Catching HTTP errors:")
try:
    client._get("https://us.api.iheart.com/api/v3/search/all")
    # (would succeed normally; showing the pattern)
except requests.HTTPError as exc:
    print(f"   HTTPError: {exc}")
except requests.ConnectionError as exc:
    print(f"   ConnectionError — network unavailable: {exc}")
except requests.Timeout:
    print("   Timeout — server did not respond in time")

# ── Empty results ─────────────────────────────────────────────────────────
print("\n3. Handling empty results safely:")
client = IHeartRadio()

# next() with a default never raises StopIteration
station = next(client.search_stations("zzz_no_such_station_xyz"), None)
if station is None:
    print("   No stations found — got None, not an exception.")

# or collect everything into a list
stations = list(client.search_stations("jazz"))
print(f"   list() approach: {len(stations)} stations returned.")

# ── Iterating safely ──────────────────────────────────────────────────────
print("\n4. Wrapping the whole iterator:")

def safe_iter(gen, label="result"):
    try:
        yield from gen
    except requests.RequestException as exc:
        print(f"   [warn] {label} failed mid-iteration: {exc}")

for station in safe_iter(client.search_stations("rock"), "stations"):
    print(f"   {station.title}")
    break  # only show one for demo

print("\nDone.")
