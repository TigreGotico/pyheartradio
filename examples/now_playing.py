"""Now playing — what is currently on air for a live station.

Demonstrates get_now_playing() for building "now playing" displays,
scrobbling to Last.fm/ListenBrainz, or triggering metadata lookups.

Run:
    python examples/now_playing.py
    python examples/now_playing.py "KROQ"
"""
import sys
from pyheartradio import IHeartRadio

client = IHeartRadio()
query = sys.argv[1] if len(sys.argv) > 1 else "classic rock"

print(f'Searching for stations: "{query}"\n')

stations = list(client.search_stations(query, max_results=5))
if not stations:
    print("No stations found.")
    raise SystemExit(1)

print(f"{'Station':<35}  {'Now playing'}")
print(f"{'-'*35}  {'-'*40}")

for station in stations:
    np = client.get_now_playing(station.id)
    if np.title and np.artist:
        now = f"{np.artist} — {np.title}"
        if np.duration:
            mins, secs = divmod(np.duration, 60)
            now += f"  ({mins}:{secs:02d})"
    elif np.title:
        now = np.title
    else:
        now = "(no metadata)"
    print(f"  {station.title:<33}  {now}")

# --- metadatarr signals ---
print()
print("First station as metadatarr Signals:")
np = client.get_now_playing(stations[0].id)
if np.title:
    sig = np.to_signals()
    for k, v in sig.items():
        print(f"  {k}: {v!r}")
    print()
    print("  → pass to Signals(**np.to_signals()) for cross-provider resolution")
else:
    print("  (no track data available right now)")
