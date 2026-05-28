"""Unified search — search() vs individual search methods.

search() makes one API call and returns all entity types at once.
This is efficient for "universal search" UIs but has a trade-off:
Artist results are stubs (id + title + image only). For full artist
profiles (albums, tracks, related artists), use search_artist().

Run:
    python examples/unified_search.py
    python examples/unified_search.py "Radiohead"
"""
import sys
from pyheartradio import IHeartRadio

client = IHeartRadio()
query = sys.argv[1] if len(sys.argv) > 1 else "radiohead"

print(f'Unified search: "{query}"\n')

# ── Single call, all types ─────────────────────────────────────────────────
results = client.search(query, max_results=5)

print(f"  Stations  : {len(results.stations)}")
print(f"  Podcasts  : {len(results.podcasts)}")
print(f"  Artists   : {len(results.artists)}")
print(f"  Tracks    : {len(results.tracks)}")
print(f"  Playlists : {len(results.playlists)}")
print()

if results.stations:
    s = results.stations[0]
    print(f"  Top station : {s.title}  →  {s.stream}")

if results.tracks:
    t = results.tracks[0]
    print(f"  Top track   : {t.title} — {t.artist}")

if results.artists:
    a = results.artists[0]
    print(f"  Top artist  : {a.title}  (id={a.id})")
    print(f"    albums={a.albums!r}  ← stub — always empty from search()")
    print()
    print("  For full profile, use search_artist():")
    full = next(client.search_artist(a.title, max_results=1), None)
    if full:
        print(f"    albums={len(full.albums)}  tracks={len(full.tracks)}"
              f"  related={len(full.related_artists)}")

print()
print("When to use each:")
print("  search()        → universal search UI, one round-trip, all types")
print("  search_artist() → need albums / tracks / related artists")
print("  search_stations() → always returns stream-URL-enriched Station objects")
