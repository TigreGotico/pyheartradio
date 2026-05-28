"""Cross-type search — run the same query across all entity types.

Useful for building a universal search UI or testing what a given
query returns across stations, podcasts, artists, tracks, and playlists.

Run:
    python examples/search_all.py
    python examples/search_all.py "NPR"
"""
import sys
from pyheartradio import IHeartRadio

client = IHeartRadio()
query = sys.argv[1] if len(sys.argv) > 1 else "blues"

print(f'Search: "{query}"\n')

results: dict[str, list] = {
    "stations":  list(client.search_stations(query)),
    "podcasts":  list(client.search_podcast(query)),
    "artists":   list(client.search_artist(query)),
    "tracks":    list(client.search_track(query)),
    "playlists": list(client.search_playlist(query)),
}

for kind, items in results.items():
    print(f"{kind.capitalize()} ({len(items)})")
    for item in items[:3]:
        print(f"  [{item.id}] {item.title}")
    if len(items) > 3:
        print(f"  … {len(items) - 3} more")
    print()
