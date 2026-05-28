"""Direct lookups by ID — get_track, get_artist_albums, get_similar_artists.

When you already have an iHeartRadio ID (from a search result, a stored
reference, or a metadatarr ExternalIds dict) you can look up the entity
directly without running a search first.

Run:
    python examples/direct_lookups.py
"""
from pyheartradio import IHeartRadio

client = IHeartRadio()


def section(title: str) -> None:
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ── Start from a search to get a real artist ID ────────────────────────────
section("Step 1 — find an artist via search")
artist = next(client.search_artist("David Bowie"), None)
if artist is None:
    print("No results — live API unreachable?")
    raise SystemExit(0)

print(f"  Found: {artist.title}  (id={artist.id})")
artist_id = artist.id

# ── get_artist_albums ──────────────────────────────────────────────────────
section(f"get_artist_albums({artist_id})")
albums = list(client.get_artist_albums(artist_id))
print(f"  {len(albums)} album(s) returned")
for album in albums[:5]:
    year = f" ({album.year})" if album.year else ""
    id_str = f"id={album.id}" if album.id is not None else "id=None"
    print(f"    [{id_str}] {album.title}{year}")
if len(albums) > 5:
    print(f"    … {len(albums) - 5} more")

# ── get_similar_artists ────────────────────────────────────────────────────
section(f"get_similar_artists({artist_id})")
similar = list(client.get_similar_artists(artist_id))
print(f"  {len(similar)} similar artist(s)")
for s in similar[:5]:
    print(f"    [{s.id}] {s.title}")

# ── find a track ID then look it up directly ───────────────────────────────
section("Step 2 — find a track ID via search")
track_from_search = next(client.search_track("Heroes David Bowie"), None)
if track_from_search:
    track_id = track_from_search.id
    print(f"  Found via search: {track_from_search.title} (id={track_id})")

    section(f"get_track({track_id})")
    track = client.get_track(track_id)
    print(f"  Title  : {track.title}")
    print(f"  Artist : {track.artist}")
    print(f"  Album  : {track.album}")
    print(f"  IDs    : track={track.id}  artist={track.artist_id}  album={track.album_id}")
    print()
    print("  to_external_ids():", track.to_external_ids())
    print("  to_signals()     :", track.to_signals())
