# Advanced usage

## Parallel fetching and latency

`search_stations`, `search_artist`, and `get_podcast_episodes` each make
one search call plus one detail call per result.  Detail calls run in
parallel using a `ThreadPoolExecutor` so latency is roughly one network
round-trip rather than N:

```
search_stations("rock", max_results=10)
  1 × search call          ~150 ms
  10 × stream-URL lookups  ~150 ms  ← all concurrent
  ─────────────────────────────────
  total                    ~300 ms  (vs ~1.65 s serial)
```

Control concurrency with `max_workers` (default: 6):

```python
client = IHeartRadio(max_workers=10)   # more aggressive parallelism
client = IHeartRadio(max_workers=1)    # sequential — useful for debugging
```

Failed detail fetches are silently skipped; the iterator continues with
the remaining results.  Adjust `timeout` if your network has higher
latency.

## Limit result count

All search methods accept `max_results` (default: 10):

```python
station = next(client.search_stations("WNYC", max_results=1))
```

Lowering `max_results` reduces both the number of search results and the
number of parallel detail fetches, so it's the primary lever for
single-result lookups.

## Custom timeout

```python
client = IHeartRadio(timeout=5)    # 5-second per-request timeout
```

## Retry logic

Attach a `urllib3.Retry` adapter to the underlying session:

```python
from requests.adapters import HTTPAdapter, Retry
from pyheartradio import IHeartRadio

client = IHeartRadio()
retry = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
)
client.session.mount("https://", HTTPAdapter(max_retries=retry))
```

## Proxies

```python
client = IHeartRadio()
client.session.proxies = {"https": "http://proxy.example.com:8080"}
```

## Custom headers

The iHeartRadio API does not require authentication but may block clients
without a recognisable `User-Agent`:

```python
client.session.headers.update({"User-Agent": "MyApp/1.0"})
```

## Caching

Station stream URLs are extremely stable — they rarely change over months
or years.  You do not need `requests-cache` as a hard dependency; attach
any cache adapter to the session instead.

**With `requests-cache` (global):**

```python
import requests_cache
requests_cache.install_cache("iheart", expire_after=3600)
client = IHeartRadio()
```

**With `CacheControl` (session-scoped, no global side-effect):**

```python
from cachecontrol import CacheControl
client = IHeartRadio()
client.session = CacheControl(client.session)
```

**With a manual in-memory dict (zero deps, stations only):**

```python
_stream_cache: dict = {}

def cached_stream(station_id: int) -> str:
    if station_id not in _stream_cache:
        station = next(client.search_stations(str(station_id), max_results=1), None)
        if station:
            _stream_cache[station_id] = station.stream
    return _stream_cache.get(station_id, "")
```

## Iterating vs materialising

Search methods return **lazy iterators** — no HTTP calls are made until you
start consuming them.  This means you can `break` early and avoid unnecessary
requests:

```python
# Only fetches stream URLs until we find a working station
for station in client.search_stations("rock"):
    if "hls" in station.stream:
        print("Found HLS stream:", station.stream)
        break
```

Calling `list()` on the iterator fetches all results at once.

## Reusing a client

One client instance, one `requests.Session`.  Use the same instance across
your whole application to benefit from connection keep-alive:

```python
# module-level singleton
_client: IHeartRadio | None = None

def get_client() -> IHeartRadio:
    global _client
    if _client is None:
        _client = IHeartRadio(timeout=8)
    return _client
```

## Closing the session

For short-lived scripts this is handled automatically at process exit.
In long-running services you can close the session explicitly:

```python
client.session.close()
```

## Thread safety

`requests.Session` is not thread-safe.  Create one `IHeartRadio` instance
per thread, or protect a shared instance with a `threading.Lock`.

## Using dataclasses output with other libraries

All models are plain `dataclasses` with no dependencies.

**Convert to dict:**

```python
from dataclasses import asdict
d = asdict(station)
```

**JSON:**

```python
import json, dataclasses
json.dumps(dataclasses.asdict(station))
```

**pandas:**

```python
import pandas as pd, dataclasses
df = pd.DataFrame([dataclasses.asdict(s) for s in client.search_stations("jazz")])
```

**attrs / pydantic wrapping:**

All fields have simple Python types (`int`, `str`, `Optional[int]`,
`List[dict]`) so they deserialise cleanly into any schema library.
