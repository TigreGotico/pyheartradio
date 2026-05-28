"""Artist discovery — search an artist, inspect their profile,
then expand into related artists.

Shows the nested structure of an Artist result.

Run:
    python examples/artist_discovery.py
    python examples/artist_discovery.py "The Beatles"
"""
import sys
from pyheartradio import IHeartRadio

client = IHeartRadio()
query = sys.argv[1] if len(sys.argv) > 1 else "David Bowie"

print(f'Searching for artist: "{query}"\n')

artist = next(client.search_artist(query), None)
if artist is None:
    print("No results.")
    raise SystemExit(1)

print(f"  Name    : {artist.title}")
print(f"  ID      : {artist.id}")
print(f"  Image   : {artist.image}")
print()

if artist.albums:
    print(f"  Albums ({len(artist.albums)} total):")
    for album in artist.albums[:5]:
        title = album.get("title") or album.get("name") or str(album)
        year = album.get("year") or album.get("releaseYear", "")
        print(f"    - {title}  {year}")
    if len(artist.albums) > 5:
        print(f"    … {len(artist.albums) - 5} more")
    print()

if artist.tracks:
    print(f"  Top tracks ({len(artist.tracks)} total):")
    for t in artist.tracks[:5]:
        title = t.get("title") or t.get("name") or str(t)
        print(f"    - {title}")
    print()

if artist.related_artists:
    print(f"  Related artists ({len(artist.related_artists)} total):")
    for r in artist.related_artists[:5]:
        name = r.get("name") or r.get("artistName") or str(r)
        print(f"    - {name}")
    print()

    # expand one related artist
    rel_name = artist.related_artists[0].get("name") or artist.related_artists[0].get("artistName")
    if rel_name:
        print(f'  Expanding first related artist: "{rel_name}"')
        rel = next(client.search_artist(rel_name), None)
        if rel:
            print(f"    Albums: {len(rel.albums)}  Tracks: {len(rel.tracks)}")
