# Advanced usage

## Custom timeout

```python
client = IHeartRadio(timeout=5)    # 5-second global timeout
```

The timeout applies to every individual HTTP call.  Some methods make two
calls per result (stations, artists) so they can take up to `2 × timeout`
seconds per item in the worst case.

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

## Limiting results

All methods use `maxRows=10` by default.  The client does not expose this
parameter today, but you can cap iteration yourself:

```python
import itertools
top3 = list(itertools.islice(client.search_stations("jazz"), 3))
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
