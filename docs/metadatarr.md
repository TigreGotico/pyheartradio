# metadatarr integration

pyheartradio is designed to plug into the metadatarr entity/resolution layer
with zero glue code.  Every model exposes `to_external_ids()` and
`to_signals()` that map directly onto mediavocab's `ExternalIds` and `Signals`.

## Canonical IDs

iHeartRadio uses plain numeric IDs.  They land in `ExternalIds.extra` under
these keys:

| Entity | Key | Example |
|---|---|---|
| Station | `iheart_station_id` | `"7556"` |
| Podcast | `iheart_podcast_id` | `"1234"` |
| Episode | `iheart_episode_id` | `"9999"` |
| Artist | `iheart_artist_id` | `"100"` |
| Track | `iheart_track_id` | `"555"` |
| Playlist | `iheart_playlist_id` | `"42"` |

Podcast episodes also carry `iheart_podcast_id` so the parent show is
always recoverable from a single episode record.

Track results additionally carry `iheart_artist_id` when available.

## Stream URLs

`stream_url` is the key the mediavocab `ExternalIds.streams` property scans
when building playable `Stream` objects.  pyheartradio sets this key on any
model that has a direct audio URL:

| Model | `stream_url` set? | `Stream.platform` |
|---|---|---|
| `Station` | When `.stream` is non-empty | `"radio"` |
| `PodcastEpisode` | When `.stream` is non-empty | `"radio"` |
| `Track` | Never — not available from API | — |

So this always works:

```python
from mediavocab.models import ExternalIds
from pyheartradio import IHeartRadio

client = IHeartRadio()
station = next(client.search_stations("jazz"))

ids = ExternalIds.from_dict(station.to_external_ids())
for s in ids.streams:
    print(s.platform, s.url)   # → radio  https://…
```

## Signals

`to_signals()` returns a dict keyed by `Signals` field names:

| Field | Station | Podcast/Episode | Track | Artist |
|---|---|---|---|---|
| `title` | ✓ | ✓ | ✓ | ✓ |
| `medium` | `"radio"` | `"podcast"` | `"music"` | `"music"` |
| `artist` | — | — | ✓ when set | — |
| `album` | — | — | ✓ when set | — |
| `duration` | — | ✓ when set | — | — |

```python
from mediavocab.models.signals import Signals

track = next(client.search_track("Heroes"))
signals = Signals(**track.to_signals())
# Signals(title="Heroes", medium=<MediaType.MUSIC>, artist="David Bowie", album="Heroes")
```

## ProviderMatch — wrapping results for metadatarr resolution

To run a pyheartradio result through `metadatarr.resolve.consolidate` or
`resolve`, wrap it in a `ProviderMatch`:

```python
from mediavocab.models import ExternalIds
from mediavocab.models.signals import Signals
from metadatarr.resolve.entities import EntityRole, ProviderEntity
from metadatarr.resolve.base import ProviderMatch, resolve

from pyheartradio import IHeartRadio

client = IHeartRadio()
artist = next(client.search_artist("David Bowie"))

match = ProviderMatch(
    provider="iheart",
    confidence=0.7,
    signals=Signals(**artist.to_signals()),
    external_ids=ExternalIds.from_dict(artist.to_external_ids()),
    relations={
        EntityRole.ARTIST: [
            ProviderEntity(
                role=EntityRole.ARTIST,
                name=artist.title,
                image_url=artist.image,
                external_ids=ExternalIds.from_dict(artist.to_external_ids()),
            )
        ]
    },
)

# Pass to metadatarr resolve alongside other provider matches
result = resolve(Signals(**artist.to_signals()), extra_matches=[match])
print(result.external_ids)
```

## EntityRole mapping

| pyheartradio entity | Recommended `EntityRole` |
|---|---|
| Station | `EntityRole.CHANNEL` |
| Podcast | `EntityRole.CHANNEL` |
| Artist | `EntityRole.ARTIST` |

## Stations in mappings.toml

If you use metadatarr's `mappings.toml` to maintain a curated station list,
iHeartRadio stations can supplement it by providing the `stream_url` and
`iheart_station_id` as external IDs:

```python
# Discover stream URL programmatically, then persist to mappings.toml
station = next(client.search_stations("WNYC"))
ids = station.to_external_ids()
print(f'stream_url = "{ids["stream_url"]}"')
print(f'iheart_station_id = "{ids["iheart_station_id"]}"')
```

Resulting `mappings.toml` entry:

```toml
[[channel]]
name               = "WNYC"
iheart_station_id  = "7556"
stream_url         = "https://fm939.wnyc.org/wnycfm.aac"
```

## Artist cross-resolution

iHeartRadio artist IDs alone are not enough for cross-provider merging —
they have no known mapping to MusicBrainz or Wikidata.  The recommended
approach is to use the artist name as the primary `Signals.title` signal
and let metadatarr's MusicBrainz / Wikidata providers fill in the
authoritative IDs:

```python
from metadatarr.resolve.base import resolve
from mediavocab.models.signals import Signals

artist = next(client.search_artist("David Bowie"))
result = resolve(Signals(**artist.to_signals()))
print(result.external_ids.musicbrainz_artist)   # "5441c29d-3602-4898-b1a1-b77fa23b8e50"
print(result.external_ids.wikidata)             # "Q5383"
```

The `iheart_artist_id` is preserved in `result.external_ids.extra` so it
round-trips without data loss.
