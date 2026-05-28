"""Canonical IDs and ExternalIds integration.

Every pyheartradio model exposes two helpers:

  model.to_external_ids()  → Dict[str, str]  — for ExternalIds.from_dict()
  model.to_signals()       → Dict[str, Any]  — for Signals(**...)

This script shows the raw output of both helpers for each entity type
and explains the key naming conventions used in the extra dict.

Run:
    python examples/external_ids.py
"""
from pprint import pprint
from pyheartradio.models import Artist, Playlist, Podcast, PodcastEpisode, Station, Track

print("=" * 60)
print("  pyheartradio canonical ID conventions")
print("=" * 60)

# ── Station ───────────────────────────────────────────────────────────────
station = Station(
    id=7556,
    title="KROQ-FM",
    description="Alternative Los Angeles",
    stream="https://stream.example.com/kroq.mp3",
    image="https://cdn.iheart.com/kroq.jpg",
)
print("\n── Station ──")
print("to_external_ids():")
pprint(station.to_external_ids())
# → {"iheart_station_id": "7556", "stream_url": "https://..."}
#   stream_url is read by ExternalIds.streams → Stream(platform="radio")
print("to_signals():")
pprint(station.to_signals())

# ── Podcast ───────────────────────────────────────────────────────────────
podcast = Podcast(id=1234, title="Radiolab")
print("\n── Podcast ──")
pprint(podcast.to_external_ids())
pprint(podcast.to_signals())

# ── PodcastEpisode ────────────────────────────────────────────────────────
ep = PodcastEpisode(
    id=9999,
    podcast_id=1234,
    title="Colors",
    duration=3240,
    stream="https://media.iheart.com/ep9999.mp3",
)
print("\n── PodcastEpisode ──")
pprint(ep.to_external_ids())
# → {"iheart_episode_id": "9999", "iheart_podcast_id": "1234", "stream_url": "..."}
pprint(ep.to_signals())

# ── Track ─────────────────────────────────────────────────────────────────
track = Track(id=555, title="Heroes", artist="David Bowie", album="Heroes",
              artist_id=100, album_id=200)
print("\n── Track ──")
pprint(track.to_external_ids())
pprint(track.to_signals())

# ── Artist ────────────────────────────────────────────────────────────────
artist = Artist(id=100, title="David Bowie")
print("\n── Artist ──")
pprint(artist.to_external_ids())
pprint(artist.to_signals())

# ── Playlist ──────────────────────────────────────────────────────────────
pl = Playlist(id=42, title="80s Hits", url="https://www.iheart.com/playlist/42")
print("\n── Playlist ──")
pprint(pl.to_external_ids())
pprint(pl.to_signals())

# ── Integration with mediavocab.ExternalIds ───────────────────────────────
print()
print("=" * 60)
print("  Integration with mediavocab.ExternalIds")
print("=" * 60)
try:
    from mediavocab.models import ExternalIds
    ids = ExternalIds.from_dict(station.to_external_ids())
    print(f"\n  ExternalIds.from_dict(station.to_external_ids())")
    print(f"  ids.extra = {ids.extra}")
    print(f"  ids.streams:")
    for s in ids.streams:
        print(f"    Stream(platform={s.platform!r}, url={s.url!r})")
except ImportError:
    print("\n  (mediavocab not installed — skipping live demo)")
    print("  When available: ExternalIds.from_dict(station.to_external_ids())")
    print("  .streams → [Stream(platform='radio', url='...')]")
