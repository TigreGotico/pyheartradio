"""metadatarr integration — resolve iHeartRadio results through the
metadatarr entity/signal layer.

Demonstrates three patterns:

1. Station  → EntityRole.CHANNEL + stream_url in ExternalIds → play queue
2. Artist   → EntityRole.ARTIST  + Signals → cross-provider resolution
3. Podcast  → EntityRole.CHANNEL + episode stream URLs

Requires:  pip install metadatarr mediavocab

Run:
    python examples/metadatarr_bridge.py
"""
from __future__ import annotations

try:
    from mediavocab.models import ExternalIds
    from mediavocab.models.signals import Signals
    from mediavocab import MediaType
    from metadatarr.resolve.entities import EntityRole, ProviderEntity
    from metadatarr.resolve.base import ProviderMatch, consolidate
    HAS_METADATARR = True
except ImportError:
    HAS_METADATARR = False

from pyheartradio import IHeartRadio
from pyheartradio.models import Artist, PodcastEpisode, Station

client = IHeartRadio()


# ── Pattern 1: Stations → play queue via ExternalIds.streams ──────────────

def station_play_queue(query: str) -> list[tuple[str, str]]:
    """Search stations and return (name, stream_url) pairs via ExternalIds."""
    queue: list[tuple[str, str]] = []
    for station in client.search_stations(query):
        if HAS_METADATARR:
            ids = ExternalIds.from_dict(station.to_external_ids())
            for stream in ids.streams:
                if stream.platform == "radio":
                    queue.append((station.title, stream.url))
        else:
            # fallback — stream is on the model directly
            if station.stream:
                queue.append((station.title, station.stream))
    return queue


print("=" * 60)
print("  Pattern 1 — Station play queue")
print("=" * 60)
for name, url in station_play_queue("jazz"):
    print(f"  {name:<35}  {url[:50]}…")


# ── Pattern 2: Artist → metadatarr Signals → cross-provider resolve ───────

def artist_to_provider_match(artist: Artist) -> "ProviderMatch | None":
    """Wrap a pyheartradio Artist as a ProviderMatch for metadatarr."""
    if not HAS_METADATARR:
        return None
    signals = Signals(**artist.to_signals())
    external_ids = ExternalIds.from_dict(artist.to_external_ids())
    entity = ProviderEntity(
        role=EntityRole.ARTIST,
        name=artist.title,
        image_url=artist.image,
        external_ids=external_ids,
    )
    return ProviderMatch(
        provider="iheart",
        confidence=0.7,
        signals=signals,
        external_ids=external_ids,
        relations={EntityRole.ARTIST: [entity]},
    )


print()
print("=" * 60)
print("  Pattern 2 — Artist → ProviderMatch")
print("=" * 60)
artist = next(client.search_artist("David Bowie"), None)
if artist and HAS_METADATARR:
    match = artist_to_provider_match(artist)
    print(f"  ProviderMatch provider  : {match.provider}")
    print(f"  ProviderMatch confidence: {match.confidence}")
    print(f"  Signals.title           : {match.signals.title}")
    print(f"  ExternalIds.extra       : {match.external_ids.extra}")
elif artist:
    print(f"  Artist: {artist.title}  (id={artist.id})")
    print(f"  to_external_ids: {artist.to_external_ids()}")
    print(f"  to_signals     : {artist.to_signals()}")
    print("  (install metadatarr for full resolve demo)")


# ── Pattern 3: Podcast episodes → stream URLs ─────────────────────────────

print()
print("=" * 60)
print("  Pattern 3 — Podcast episodes → ExternalIds streams")
print("=" * 60)
podcast = next(client.search_podcast("Radiolab"), None)
if podcast:
    for ep in client.get_podcast_episodes(podcast.id):
        if HAS_METADATARR:
            ids = ExternalIds.from_dict(ep.to_external_ids())
            streams = ids.streams
            label = f"Stream(platform={streams[0].platform!r})" if streams else "(no stream)"
        else:
            label = ep.stream[:60] if ep.stream else "(no stream)"
        print(f"  {ep.title[:50]:<50}  {label}")
        break  # first episode only for demo
