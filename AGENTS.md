# AGENTS.md — pyheartradio

Python client for the iHeartRadio public API (search and stream live stations, podcasts, artists, tracks, playlists; no API key required).

## Setup

```bash
pip install -e .
pip install -e .[test]   # pytest, pytest-timeout, pytest-cov, vcrpy, pytest-vcr
```

Single runtime dependency: `requests`.

## Test

```bash
pytest
```

`testpaths = ["test"]` is set in `pyproject.toml`. The offline suite (`test_mock.py`, `test_models.py`, `test_edge_cases.py`, `test_import.py`) requires no network. `test/test_live.py` hits the real API — it is excluded from the standard CI build and runs only via `nightly-live.yml` or manually:

```bash
pytest test/test_live.py -v
```

## Lint

Ruff is configured (`[tool.ruff]`, line-length 100, rules `E,F,W,I`, ignoring `E501`):

```bash
ruff check pyheartradio test
```

## Layout

- `pyheartradio/__init__.py` — the `IHeartRadio` client class. All HTTP endpoints are class attributes (`search_url`, `station_stream_url`, `podcast_episodes_url`, etc.). Search methods return iterators; `_parallel()` runs per-item detail fetches concurrently via a `ThreadPoolExecutor`, preserving result order and skipping items whose fetch raised. `_pick_stream()` selects a stream by `_STREAM_FORMAT_PREFERENCE`.
- `pyheartradio/models.py` — typed `@dataclass` models (`Station`, `NowPlaying`, `Album`, `Podcast`, `PodcastEpisode`, `Track`, `Artist`, `Playlist`, `SearchResults`). Stdlib-only. Every model exposes `to_external_ids()` and `to_signals()` for mediavocab/metadatarr bridging.
- `pyheartradio/version.py` — version block; do not edit (see Conventions).
- `test/` — mock-based unit tests, model tests, edge cases, import smoke test, live integration tests, and `license_tests.py`.
- `docs/` — quickstart, models, methods, metadatarr integration, advanced.
- `examples/` — runnable usage scripts incl. `metadatarr_bridge.py`.

## Conventions (Org hard rules)

- Branches: `dev` (work) / `master` (stable). NEVER `main`.
- Never edit `version.py`; gh-automations bumps semver from conventional-commit prefixes (`feat:`, `fix:`, `feat!:`).
- New repos private by default.
- Commit identity: `JarbasAi <jarbasai@mailfence.com>`.
- Reference `OpenVoiceOS/gh-automations` reusable workflows at `@dev`.
- No Neon / `neon-*` references.
- No meta-commentary (no history, dates, "before times"). Describe current state only.
- CI is provided by OpenVoiceOS/gh-automations reusable workflows.

## Gotchas

- The API exposes no stream URL for individual tracks — `search_track()` / `get_track()` return metadata only. Use `search_stations()` or `search_artist()` for playable content.
- `search_stations()` silently drops stations with no `streams` dict (`_station_from_raw` returns `None`).
- `search()` returns Artist stubs (id/title/image only); call `search_artist()` for albums/tracks/related artists.
- `get_now_playing()` and `get_track()` use explicit `isinstance(..., dict)` checks rather than `or`-chaining, because an empty dict is falsy and would wrongly fall through.
- The client uses a plain `requests.Session` (no built-in caching). Attach `requests_cache` or `CacheControl` to `client.session` if needed.
- `Album.id` may be `None` when the API returns partial data (e.g. from an artist profile).
