# Quickstart

Get your first results in under 5 minutes.

## Install

```bash
pip install pyheartradio
```

## Create a client

```python
from pyheartradio import IHeartRadio

client = IHeartRadio()
```

No API key, no account, no configuration required.

To customise the HTTP timeout (default is 10 seconds):

```python
client = IHeartRadio(timeout=5)
```

## Search for a radio station

```python
for station in client.search_stations("classic rock"):
    print(station.title)         # "Classic Rock 101.1"
    print(station.stream)        # "https://…/stream.mp3"
    print(station.description)
    print(station.image)
    print(station.id)            # numeric iHeartRadio ID
```

Pass the stream URL directly to any media player:

```bash
mpv "https://…/stream.mp3"
```

## Search for a podcast

```python
for podcast in client.search_podcast("true crime"):
    print(podcast.title)
    print(podcast.id)
```

### Get episodes for that podcast

```python
podcast = next(client.search_podcast("Radiolab"))
for ep in client.get_podcast_episodes(podcast.id):
    print(ep.title, ep.duration, ep.stream)
```

Each episode has a direct `.stream` URL you can play immediately.

## Search for an artist

```python
for artist in client.search_artist("David Bowie"):
    print(artist.title)
    print(len(artist.albums))
    print(len(artist.related_artists))
```

## Search for a track

```python
for track in client.search_track("Heroes"):
    print(track.title, track.artist, track.album)
```

> **Note:** iHeartRadio does not expose stream URLs for individual tracks
> via the public API.  Use stations or podcast episodes for playable content.

## Search for a playlist

```python
for pl in client.search_playlist("workout"):
    print(pl.title, pl.url)
```

## Read a single result safely

Use `next()` with a default to avoid `StopIteration` when there are no results:

```python
station = next(client.search_stations("WNYC"), None)
if station:
    print(station.stream)
```

## Collect all results

All search methods return iterators.  Wrap in `list()` to materialise them:

```python
stations = list(client.search_stations("jazz"))
print(f"{len(stations)} stations found")
```

## Next steps

- [Data models](models.md) — what fields each result type carries
- [API methods](methods.md) — all parameters
- [metadatarr integration](metadatarr.md) — canonical IDs, cross-provider resolution
