"""Edge-case and coverage-gap tests.

Covers branches not exercised by test_mock.py or test_models.py:
  - _pick_stream edge cases
  - _search_payload structure and defaults
  - _parallel with 0 and 1 items
  - max_results forwarding for all search methods
  - multi-result ordering for search_artist and unified search
  - get_artist_albums / get_similar_artists response key variants
  - get_now_playing trackTitle / imageUrl field aliases
  - Optional-ID models (Track, PodcastEpisode, Album without IDs)
  - SearchResults partial population
  - NowPlaying no-duration signals
  - LOG.debug call on parallel fetch failure
  - search() station with hits:[] uses _hit_from_detail safely
  - _station_from_raw with null streams value
"""
import logging
from threading import Lock
from unittest.mock import MagicMock, patch

import pytest

from pyheartradio import IHeartRadio
from pyheartradio import _STREAM_FORMAT_PREFERENCE
from pyheartradio.models import (
    Album, Artist, NowPlaying, Playlist, Podcast, PodcastEpisode,
    SearchResults, Station, Track,
)


@pytest.fixture
def client():
    return IHeartRadio()


def _resp(data):
    m = MagicMock()
    m.json.return_value = data
    m.raise_for_status.return_value = None
    return m


# ---------------------------------------------------------------------------
# _pick_stream
# ---------------------------------------------------------------------------

class TestPickStream:
    def test_empty_returns_empty_string(self):
        assert IHeartRadio._pick_stream({}) == ""

    def test_preference_order_beats_insertion_order(self):
        # hls comes first in dict but shoutcast_stream should win
        streams = {"hls_stream": "http://hls", "shoutcast_stream": "http://shout"}
        assert IHeartRadio._pick_stream(streams) == "http://shout"

    def test_unknown_format_falls_back_to_first(self):
        streams = {"custom_stream": "http://custom", "other": "http://other"}
        result = IHeartRadio._pick_stream(streams)
        assert result in ("http://custom", "http://other")  # first of unknown

    def test_all_preference_keys_tried_in_order(self):
        # only hls_stream present — should still be returned
        streams = {"hls_stream": "http://hls"}
        assert IHeartRadio._pick_stream(streams) == "http://hls"

    def test_preference_constant_is_non_empty_tuple(self):
        assert isinstance(_STREAM_FORMAT_PREFERENCE, tuple)
        assert len(_STREAM_FORMAT_PREFERENCE) > 0

    def test_picks_first_match_in_preference(self):
        # shoutcast_stream is earlier in preference than hls_stream
        shout_idx = _STREAM_FORMAT_PREFERENCE.index("shoutcast_stream")
        hls_idx = _STREAM_FORMAT_PREFERENCE.index("hls_stream")
        assert shout_idx < hls_idx


# ---------------------------------------------------------------------------
# _search_payload
# ---------------------------------------------------------------------------

class TestSearchPayload:
    def test_all_flags_default_false(self, client):
        payload = client._search_payload("jazz", 10)
        for flag in ("station", "artist", "track", "playlist", "podcast"):
            assert payload[flag] == "false"

    def test_bundle_always_false(self, client):
        payload = client._search_payload("jazz", 10, station="true")
        assert payload["bundle"] == "false"

    def test_max_results_set(self, client):
        assert client._search_payload("x", 7)["maxRows"] == 7

    def test_flag_override(self, client):
        payload = client._search_payload("jazz", 10, station="true", podcast="true")
        assert payload["station"] == "true"
        assert payload["podcast"] == "true"
        assert payload["artist"] == "false"

    def test_keywords_set(self, client):
        payload = client._search_payload("my query", 5)
        assert payload["keywords"] == "my query"


# ---------------------------------------------------------------------------
# _parallel edge cases
# ---------------------------------------------------------------------------

class TestParallel:
    def test_empty_items_returns_empty(self, client):
        assert client._parallel(lambda x: x, []) == []

    def test_single_item_returns_one_pair(self, client):
        results = client._parallel(lambda x: x * 2, [5])
        assert results == [(5, 10)]

    def test_preserves_order_with_multiple_items(self, client):
        # fn is fast for even, slow for odd — order must still match input
        import time
        def fn(x):
            if x % 2 != 0:
                time.sleep(0.01)
            return x * 10
        results = client._parallel(fn, [1, 2, 3, 4])
        assert [item for item, _ in results] == [1, 2, 3, 4]
        assert [res for _, res in results] == [10, 20, 30, 40]

    def test_exception_logged_and_item_skipped(self, client, caplog):
        def boom(x):
            if x == 2:
                raise ValueError("fetch failed")
            return x
        with caplog.at_level(logging.DEBUG, logger="pyheartradio"):
            results = client._parallel(boom, [1, 2, 3])
        # item 2 skipped, 1 and 3 remain
        assert len(results) == 2
        assert results[0] == (1, 1)
        assert results[1] == (3, 3)
        assert any("fetch failed" in r.message for r in caplog.records)

    def test_all_items_fail_returns_empty(self, client):
        results = client._parallel(lambda x: (_ for _ in ()).throw(RuntimeError()), [1, 2])
        assert results == []


# ---------------------------------------------------------------------------
# max_results forwarded for all search methods
# ---------------------------------------------------------------------------

class TestMaxResults:
    def _capture_payload(self, client, method_name, *args, **kwargs):
        """Call method, capture the params dict from the first _get call."""
        captured = {}
        original = client._get
        def intercepting_get(url, params=None):
            if not captured:
                captured["params"] = params
            return {"results": {}}
        with patch.object(client, "_get", side_effect=intercepting_get):
            try:
                list(getattr(client, method_name)(*args, **kwargs))
            except (TypeError, StopIteration):
                pass
        return captured.get("params", {})

    def test_search_podcast_max_results(self, client):
        params = self._capture_payload(client, "search_podcast", "x", max_results=3)
        assert params["maxRows"] == 3

    def test_search_track_max_results(self, client):
        params = self._capture_payload(client, "search_track", "x", max_results=2)
        assert params["maxRows"] == 2

    def test_search_artist_max_results(self, client):
        params = self._capture_payload(client, "search_artist", "x", max_results=4)
        assert params["maxRows"] == 4

    def test_search_playlist_max_results(self, client):
        params = self._capture_payload(client, "search_playlist", "x", max_results=1)
        assert params["maxRows"] == 1

    def test_search_unified_max_results(self, client):
        params = self._capture_payload(client, "search", "x", max_results=6)
        assert params["maxRows"] == 6

    def test_search_unified_enables_all_flags(self, client):
        params = self._capture_payload(client, "search", "x")
        for flag in ("station", "artist", "track", "playlist", "podcast"):
            assert params[flag] == "true", f"flag {flag!r} should be 'true'"


# ---------------------------------------------------------------------------
# search_artist multi-result ordering
# ---------------------------------------------------------------------------

def test_search_artist_ordering_preserved(client):
    search_data = {
        "results": {
            "artists": [
                {"id": 1, "name": "Artist A", "image": ""},
                {"id": 2, "name": "Artist B", "image": ""},
                {"id": 3, "name": "Artist C", "image": ""},
            ]
        }
    }
    profiles = [
        {"albums": [{"id": i * 10, "title": f"Album {i}"}], "tracks": [], "relatedTo": []}
        for i in (1, 2, 3)
    ]
    call_count = 0
    lock = Lock()

    def side_effect(url, params=None, timeout=None):
        nonlocal call_count
        with lock:
            call_count += 1
            count = call_count
        if count == 1:
            return _resp(search_data)
        # profiles returned in reverse order to test ordering
        idx = (3 - (count - 1)) % 3
        return _resp(profiles[idx])

    with patch.object(client.session, "get", side_effect=side_effect):
        artists = list(client.search_artist("any"))

    assert len(artists) == 3
    assert artists[0].id == 1
    assert artists[1].id == 2
    assert artists[2].id == 3


# ---------------------------------------------------------------------------
# get_artist_albums — response key variants
# ---------------------------------------------------------------------------

def test_get_artist_albums_data_key(client):
    data = {"data": [{"id": 5, "title": "Album via data key", "year": 2000}]}
    with patch.object(client.session, "get", return_value=_resp(data)):
        albums = list(client.get_artist_albums(1))
    assert len(albums) == 1
    assert albums[0].title == "Album via data key"


def test_get_artist_albums_empty_response(client):
    with patch.object(client.session, "get", return_value=_resp({})):
        albums = list(client.get_artist_albums(1))
    assert albums == []


def test_get_artist_albums_no_id_in_response(client):
    data = {"albums": [{"title": "No ID Album", "artistName": "X"}]}
    with patch.object(client.session, "get", return_value=_resp(data)):
        albums = list(client.get_artist_albums(1))
    assert len(albums) == 1
    assert albums[0].id is None
    assert "iheart_album_id" not in albums[0].to_external_ids()


# ---------------------------------------------------------------------------
# get_similar_artists — response key variants
# ---------------------------------------------------------------------------

def test_get_similar_artists_data_key(client):
    data = {"data": [{"id": 9, "name": "Similar via data key"}]}
    with patch.object(client.session, "get", return_value=_resp(data)):
        similar = list(client.get_similar_artists(1))
    assert len(similar) == 1
    assert similar[0].title == "Similar via data key"


def test_get_similar_artists_empty_response(client):
    with patch.object(client.session, "get", return_value=_resp({})):
        assert list(client.get_similar_artists(1)) == []


# ---------------------------------------------------------------------------
# get_now_playing — field aliases
# ---------------------------------------------------------------------------

def test_get_now_playing_trackTitle_alias(client):
    data = {"currentTrack": {"trackTitle": "Alt Title", "artistName": "Alt Artist"}}
    with patch.object(client.session, "get", return_value=_resp(data)):
        np = client.get_now_playing(1)
    assert np.title == "Alt Title"
    assert np.artist == "Alt Artist"


def test_get_now_playing_imageUrl_alias(client):
    data = {"currentTrack": {"title": "T", "artistName": "A",
                              "imageUrl": "http://img.example.com"}}
    with patch.object(client.session, "get", return_value=_resp(data)):
        np = client.get_now_playing(1)
    assert np.image == "http://img.example.com"


def test_get_now_playing_no_duration_in_signals():
    np = NowPlaying(station_id=1, title="T", artist="A")
    assert "duration" not in np.to_signals()


def test_get_now_playing_track_key_fallback(client):
    data = {"track": {"title": "Fallback Song", "artistName": "Fallback Artist"}}
    with patch.object(client.session, "get", return_value=_resp(data)):
        np = client.get_now_playing(1)
    assert np.title == "Fallback Song"


# ---------------------------------------------------------------------------
# search() — station hits:[] path is safe
# ---------------------------------------------------------------------------

def test_search_unified_station_empty_hits_skipped(client):
    response = {
        "results": {
            "stations": [{"id": 1, "name": "Ghost FM"}],
            "podcasts": [], "artists": [], "tracks": [], "playlists": [],
        }
    }
    empty_hits = {"hits": []}
    with patch.object(client.session, "get",
                      side_effect=[_resp(response), _resp(empty_hits)]):
        results = client.search("ghost")
    assert results.stations == []   # no crash, station silently skipped
    assert not results


# ---------------------------------------------------------------------------
# Optional-ID models
# ---------------------------------------------------------------------------

class TestOptionalIds:
    def test_track_no_artist_id_external_ids(self):
        t = Track(id=5, title="T")
        ids = t.to_external_ids()
        assert "iheart_track_id" in ids
        assert "iheart_artist_id" not in ids

    def test_track_no_album_id_external_ids(self):
        t = Track(id=5, title="T", artist_id=10)
        ids = t.to_external_ids()
        assert "iheart_artist_id" in ids

    def test_podcast_episode_no_podcast_id(self):
        ep = PodcastEpisode(id=9, title="Ep")
        ids = ep.to_external_ids()
        assert "iheart_episode_id" in ids
        assert "iheart_podcast_id" not in ids

    def test_album_no_artist_id(self):
        a = Album(id=10, title="A")
        ids = a.to_external_ids()
        assert "iheart_album_id" in ids
        assert "iheart_artist_id" not in ids

    def test_album_none_id_no_album_id_key(self):
        a = Album(id=None, title="A", artist_id=5)
        ids = a.to_external_ids()
        assert "iheart_album_id" not in ids
        assert ids["iheart_artist_id"] == "5"


# ---------------------------------------------------------------------------
# SearchResults
# ---------------------------------------------------------------------------

def test_search_results_partial_population():
    r = SearchResults(query="x",
                      stations=[Station(id=1, title="S")],
                      podcasts=[Podcast(id=2, title="P")])
    assert bool(r) is True
    assert len(r.artists) == 0
    assert len(r.tracks) == 0


def test_search_results_only_tracks():
    r = SearchResults(query="x", tracks=[Track(id=1, title="T")])
    assert bool(r) is True


# ---------------------------------------------------------------------------
# _station_from_raw edge cases
# ---------------------------------------------------------------------------

def test_station_from_raw_null_streams():
    raw = {"id": 1, "name": "X"}
    # streams key present but value is None (not a dict)
    hit = {"streams": None, "logo": "", "description": ""}
    # `hit.get("streams") or {}` treats None as falsy → {} → no station
    result = IHeartRadio._station_from_raw(raw, hit)
    assert result is None


def test_station_from_raw_empty_streams():
    raw = {"id": 1, "name": "X"}
    hit = {"streams": {}, "logo": "", "description": ""}
    assert IHeartRadio._station_from_raw(raw, hit) is None


def test_station_from_raw_populates_streams_dict():
    raw = {"id": 7, "name": "Jazz FM"}
    hit = {"streams": {"shoutcast_stream": "http://shout", "hls_stream": "http://hls"},
           "logo": "http://logo", "description": "Jazz"}
    s = IHeartRadio._station_from_raw(raw, hit)
    assert s is not None
    assert s.streams == {"shoutcast_stream": "http://shout", "hls_stream": "http://hls"}
    assert s.stream == "http://shout"  # shoutcast_stream preferred


# ---------------------------------------------------------------------------
# _hit_from_detail
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("response,expected", [
    ({}, {}),
    ({"hits": []}, {}),
    ({"hits": None}, {}),
    ({"hits": [{"id": 1}]}, {"id": 1}),
    ({"hits": [{"id": 1}, {"id": 2}]}, {"id": 1}),  # first only
])
def test_hit_from_detail_parametrized(response, expected):
    assert IHeartRadio._hit_from_detail(response) == expected


# ---------------------------------------------------------------------------
# NowPlaying.to_signals completeness
# ---------------------------------------------------------------------------

def test_now_playing_signals_full():
    np = NowPlaying(station_id=1, title="T", artist="A", album="B", duration=120)
    sig = np.to_signals()
    assert sig["title"] == "T"
    assert sig["artist"] == "A"
    assert sig["album"] == "B"
    assert sig["duration"] == 120
    assert sig["medium"] == "music"


def test_now_playing_signals_empty_fields_omitted():
    np = NowPlaying(station_id=1)
    sig = np.to_signals()
    assert "title" not in sig
    assert "artist" not in sig
    assert "album" not in sig
    assert "duration" not in sig
    assert sig["medium"] == "music"
