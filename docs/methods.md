# API methods

All methods live on the `IHeartRadio` class.

```python
from pyheartradio import IHeartRadio
client = IHeartRadio(timeout=10)
```

---

## `IHeartRadio(timeout=10)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `timeout` | `int` | `10` | HTTP request timeout in seconds |

The client creates a single `requests.Session` that is reused for all calls.
To use a custom session (e.g. with proxy settings or retry adapters) assign
it directly after construction:

```python
import requests
from requests.adapters import HTTPAdapter, Retry

client = IHeartRadio()
retry = Retry(total=3, backoff_factor=0.5)
client.session.mount("https://", HTTPAdapter(max_retries=retry))
```

---

## `search_stations(search_term)` → `Iterator[Station]`

Search for live radio stations.

| Parameter | Type | Description |
|---|---|---|
| `search_term` | `str` | Free-text query, e.g. `"jazz"`, `"WNYC"`, `"90s hits"` |

Each yielded `Station` is guaranteed to have a non-empty `.stream` URL.
Results without a playable stream are silently skipped.

**Two HTTP calls per station result** (search + stream-URL lookup).

```python
for s in client.search_stations("NPR"):
    print(s.title, s.stream)
```

---

## `search_podcast(search_term)` → `Iterator[Podcast]`

Search for podcast shows.

| Parameter | Type | Description |
|---|---|---|
| `search_term` | `str` | Show name, topic, or host |

**One HTTP call** (search only).

```python
podcast = next(client.search_podcast("Serial"), None)
```

---

## `get_podcast_episodes(podcast_id)` → `Iterator[PodcastEpisode]`

Retrieve episodes for a podcast.

| Parameter | Type | Description |
|---|---|---|
| `podcast_id` | `int` | The numeric iHeartRadio podcast ID |

**One HTTP call per episode** (episode list + per-episode stream URL lookup).

```python
for ep in client.get_podcast_episodes(podcast.id):
    print(ep.title, ep.stream)
```

---

## `search_track(search_term)` → `Iterator[Track]`

Search for music tracks.

| Parameter | Type | Description |
|---|---|---|
| `search_term` | `str` | Track title, artist, or keyword |

**One HTTP call** (search only).

> Stream URLs are not available for tracks via the public API.

```python
for t in client.search_track("Heroes David Bowie"):
    print(t.title, t.artist)
```

---

## `search_artist(search_term)` → `Iterator[Artist]`

Search for artists, with profile data (albums, top tracks, related artists).

| Parameter | Type | Description |
|---|---|---|
| `search_term` | `str` | Artist or band name |

**Two HTTP calls per artist result** (search + artist profile).

```python
for a in client.search_artist("The Beatles"):
    print(a.title, len(a.albums), "albums")
```

---

## `search_playlist(search_term)` → `Iterator[Playlist]`

Search for curated playlists.

| Parameter | Type | Description |
|---|---|---|
| `search_term` | `str` | Mood, genre, or keyword |

**One HTTP call** (search only).

```python
for pl in client.search_playlist("lo-fi study"):
    print(pl.title, pl.url)
```

---

## Error handling

All methods raise standard `requests` exceptions on network or HTTP errors:

| Exception | When |
|---|---|
| `requests.HTTPError` | Server returned 4xx or 5xx |
| `requests.ConnectionError` | Network unavailable |
| `requests.Timeout` | Request exceeded `timeout` seconds |

```python
import requests

try:
    stations = list(client.search_stations("jazz"))
except requests.HTTPError as exc:
    print(f"HTTP {exc.response.status_code}")
except requests.Timeout:
    print("Request timed out")
except requests.ConnectionError:
    print("No network")
```
