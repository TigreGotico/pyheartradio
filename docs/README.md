# pyheartradio — documentation

A Python client for the iHeartRadio public API.  Search and stream radio
stations, podcasts, artists, tracks, and playlists.

## Contents

| Document | Audience |
|---|---|
| [Quickstart](quickstart.md) | New users — get results in 5 minutes |
| [Data models](models.md) | Reference for every returned type |
| [API methods](methods.md) | Full method signatures and parameters |
| [metadatarr integration](metadatarr.md) | Cross-provider resolution and canonical IDs |
| [Advanced usage](advanced.md) | Sessions, retries, timeouts, pagination |

## Install

```bash
pip install pyheartradio
```

## Minimum example

```python
from pyheartradio import IHeartRadio

client = IHeartRadio()
for station in client.search_stations("jazz"):
    print(station.title, station.stream)
    break
```

## Where to go next

- New here?  Start with [Quickstart](quickstart.md).
- Want to wire results into a media player or metadatarr?  See [metadatarr integration](metadatarr.md).
- Need all the details on a specific method?  See [API methods](methods.md).
