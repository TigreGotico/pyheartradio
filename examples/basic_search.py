"""Basic search — the quickest way to get results.

Demonstrates all six search methods in one script.  Nothing is played;
this just shows what data comes back.

Run:
    python examples/basic_search.py
"""
from pyheartradio import IHeartRadio

client = IHeartRadio()


def section(title: str) -> None:
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ── Stations ──────────────────────────────────────────────────────────────
section("Stations — 'classic rock'")
for station in client.search_stations("classic rock"):
    print(f"  [{station.id}] {station.title}")
    print(f"       {station.stream}")
    break  # just first result for demo

# ── Podcasts ──────────────────────────────────────────────────────────────
section("Podcasts — 'true crime'")
for podcast in client.search_podcast("true crime"):
    print(f"  [{podcast.id}] {podcast.title}")
    print(f"       {podcast.description[:80]}…")
    break

# ── Podcast episodes ──────────────────────────────────────────────────────
section("First podcast → first episode")
podcast = next(client.search_podcast("Radiolab"), None)
if podcast:
    print(f"  Podcast: {podcast.title} (id={podcast.id})")
    ep = next(client.get_podcast_episodes(podcast.id), None)
    if ep:
        print(f"  Episode: {ep.title}")
        print(f"  Duration: {ep.duration}s")
        print(f"  Stream: {ep.stream}")

# ── Tracks ────────────────────────────────────────────────────────────────
section("Tracks — 'Bohemian Rhapsody'  (no stream URL from API)")
for track in client.search_track("Bohemian Rhapsody"):
    print(f"  [{track.id}] {track.title} — {track.artist} / {track.album}")
    break

# ── Artists ───────────────────────────────────────────────────────────────
section("Artists — 'David Bowie'")
for artist in client.search_artist("David Bowie"):
    print(f"  [{artist.id}] {artist.title}")
    print(f"  Albums : {len(artist.albums)}")
    print(f"  Related: {len(artist.related_artists)}")
    break

# ── Playlists ─────────────────────────────────────────────────────────────
section("Playlists — 'workout'")
for pl in client.search_playlist("workout"):
    print(f"  [{pl.id}] {pl.title}")
    print(f"       {pl.url}")
    break
