# Data models

All search methods return typed `dataclasses` instances.  Every field has a
default so partial API responses never raise `KeyError` at construction time.

## Station

Returned by `search_stations()`.

```python
@dataclass
class Station:
    id: int            # iHeartRadio station ID
    title: str         # Station name
    description: str   # One-line description (may be empty)
    image: str         # Artwork / logo URL
    stream: str        # Direct playable stream URL (HLS, MP3, or AAC)
```

Stations always have a non-empty `.stream` — results without a stream URL
are silently skipped by the client.

### Methods

#### `to_external_ids() → Dict[str, str]`

Returns a dict suitable for `ExternalIds.from_dict()`:

```python
{
    "iheart_station_id": "7556",
    "stream_url": "https://…"    # present when stream is non-empty
}
```

The `stream_url` key is recognised by `ExternalIds.streams` and surfaces as
`Stream(platform="radio")`.

#### `to_signals() → Dict[str, Any]`

```python
{"title": "KROQ-FM", "medium": "radio"}
```

---

## Podcast

Returned by `search_podcast()`.

```python
@dataclass
class Podcast:
    id: int
    title: str
    description: str
    image: str
```

Use `.id` to call `get_podcast_episodes()`.

### Methods

| Method | Returns |
|---|---|
| `to_external_ids()` | `{"iheart_podcast_id": "1234"}` |
| `to_signals()` | `{"title": "…", "medium": "podcast"}` |

---

## PodcastEpisode

Returned by `get_podcast_episodes()`.

```python
@dataclass
class PodcastEpisode:
    id: int
    title: str
    podcast_id: Optional[int]  # parent podcast ID, always set by the client
    description: str
    image: str
    duration: Optional[int]    # seconds; None when the API omits it
    stream: str                # direct audio URL
```

### Methods

`to_external_ids()` returns all three keys when set:

```python
{
    "iheart_episode_id": "9999",
    "iheart_podcast_id": "1234",
    "stream_url": "https://…"
}
```

`to_signals()` includes duration when available:

```python
{"title": "Colors", "medium": "podcast", "duration": 3240}
```

---

## Track

Returned by `search_track()`.

```python
@dataclass
class Track:
    id: int
    title: str
    artist: str
    album: str
    image: str
    artist_id: Optional[int]
    album_id: Optional[int]
```

> **No stream URL available.** iHeartRadio's public API does not expose
> playable URLs for individual tracks.

### Methods

```python
to_external_ids() → {"iheart_track_id": "555", "iheart_artist_id": "100"}
to_signals()      → {"title": "Heroes", "medium": "music",
                      "artist": "David Bowie", "album": "Heroes"}
```

---

## Artist

Returned by `search_artist()`.

```python
@dataclass
class Artist:
    id: int
    title: str               # artist / band name
    image: str
    albums: List[dict]       # raw album dicts from the artist-profile endpoint
    tracks: List[dict]       # raw top-track dicts
    related_artists: List[dict]
```

`albums`, `tracks`, and `related_artists` are raw dicts because iHeartRadio's
profile endpoint returns variably-shaped payloads.  Check the keys with
`artist.albums[0].keys()` if you need a specific field.

### Methods

```python
to_external_ids() → {"iheart_artist_id": "100"}
to_signals()      → {"title": "David Bowie", "medium": "music"}
```

---

## Playlist

Returned by `search_playlist()`.

```python
@dataclass
class Playlist:
    id: int
    title: str
    description: str
    image: str
    url: str    # web URL for the playlist page on iheart.com
```

### Methods

```python
to_external_ids() → {"iheart_playlist_id": "42"}
to_signals()      → {"title": "80s Hits", "medium": "music"}
```

---

## Common patterns

### Check if a result has a stream

```python
if station.stream:
    subprocess.run(["mpv", station.stream])
```

### Convert to a dict

Standard `dataclasses.asdict()` works on all models:

```python
from dataclasses import asdict
d = asdict(station)
```

### JSON serialisation

```python
import json, dataclasses
json.dumps(dataclasses.asdict(station))
```
