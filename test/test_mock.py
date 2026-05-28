from threading import Lock
from unittest.mock import MagicMock, patch
import pytest
from pyheartradio import IHeartRadio
from pyheartradio.models import Artist, Playlist, Podcast, PodcastEpisode, Station, Track


@pytest.fixture
def client():
    return IHeartRadio()


def _mock_get(return_value):
    mock_resp = MagicMock()
    mock_resp.json.return_value = return_value
    mock_resp.raise_for_status.return_value = None
    return mock_resp


# ---------------------------------------------------------------------------
# search_stations
# ---------------------------------------------------------------------------

def test_search_stations(client):
    search_data = {"results": {"stations": [{"id": 1, "name": "Rock FM"}]}}
    station_data = {
        "hits": [{"streams": {"shoutcast_stream": "http://stream.example.com"},
                  "logo": "http://img.example.com",
                  "description": "Best rock"}]
    }
    with patch.object(client.session, "get",
                      side_effect=[_mock_get(search_data), _mock_get(station_data)]):
        results = list(client.search_stations("rock"))

    assert len(results) == 1
    assert isinstance(results[0], Station)
    assert results[0].title == "Rock FM"
    assert results[0].stream == "http://stream.example.com"
    assert results[0].id == 1


def test_search_stations_no_streams_skipped(client):
    search_data = {"results": {"stations": [{"id": 1, "name": "Silent FM"}]}}
    station_data = {"hits": [{"streams": {}, "logo": "", "description": ""}]}
    with patch.object(client.session, "get",
                      side_effect=[_mock_get(search_data), _mock_get(station_data)]):
        results = list(client.search_stations("silent"))
    assert results == []


def test_search_stations_max_results_forwarded(client):
    search_data = {"results": {"stations": []}}
    captured = []
    orig = client._get

    def capturing_get(url, params=None):
        captured.append(params)
        return orig.__func__(client, url, params) if False else search_data  # short-circuit

    with patch.object(client, "_get", side_effect=capturing_get):
        list(client.search_stations("jazz", max_results=3))

    assert captured[0]["maxRows"] == 3


# ---------------------------------------------------------------------------
# search_podcast
# ---------------------------------------------------------------------------

def test_search_podcast(client):
    data = {
        "results": {
            "podcasts": [{"id": 42, "title": "Tech Talk",
                          "image": "http://img.example.com", "description": "Tech news"}]
        }
    }
    with patch.object(client.session, "get", return_value=_mock_get(data)):
        results = list(client.search_podcast("tech"))

    assert len(results) == 1
    assert isinstance(results[0], Podcast)
    assert results[0].title == "Tech Talk"
    assert results[0].id == 42


# ---------------------------------------------------------------------------
# get_podcast_episodes
# ---------------------------------------------------------------------------

def test_get_podcast_episodes(client):
    episodes_data = {
        "data": [{"id": 7, "title": "Episode 1", "duration": 1800,
                  "description": "Intro", "imageUrl": "http://img.example.com"}]
    }
    stream_data = {"episode": {"mediaUrl": "http://media.example.com/ep1.mp3"}}
    with patch.object(client.session, "get",
                      side_effect=[_mock_get(episodes_data), _mock_get(stream_data)]):
        results = list(client.get_podcast_episodes(42))

    assert len(results) == 1
    assert isinstance(results[0], PodcastEpisode)
    assert results[0].stream == "http://media.example.com/ep1.mp3"
    assert results[0].duration == 1800
    assert results[0].podcast_id == 42


def test_get_podcast_episodes_parallel_multiple(client):
    """Three episodes — stream URLs must be fetched concurrently, results ordered."""
    episodes_data = {
        "data": [
            {"id": 1, "title": "Ep1", "duration": 100, "description": "", "imageUrl": ""},
            {"id": 2, "title": "Ep2", "duration": 200, "description": "", "imageUrl": ""},
            {"id": 3, "title": "Ep3", "duration": 300, "description": "", "imageUrl": ""},
        ]
    }

    call_count = 0
    lock = Lock()

    def side_effect(url, params=None, timeout=None):
        nonlocal call_count
        with lock:
            call_count += 1
            count = call_count
        if count == 1:
            return _mock_get(episodes_data)
        ep_id = count - 1  # calls 2,3,4 → episode ids 1,2,3
        return _mock_get({"episode": {"mediaUrl": f"http://media.example.com/ep{ep_id}.mp3"}})

    with patch.object(client.session, "get", side_effect=side_effect):
        results = list(client.get_podcast_episodes(99))

    assert len(results) == 3
    # results must be in original order regardless of thread completion order
    assert results[0].id == 1
    assert results[1].id == 2
    assert results[2].id == 3


# ---------------------------------------------------------------------------
# search_track
# ---------------------------------------------------------------------------

def test_search_track(client):
    data = {
        "results": {
            "tracks": [{"id": 99, "title": "Song", "artistName": "Artist",
                        "albumName": "Album", "image": "http://img.example.com",
                        "artistId": 5, "albumId": 10}]
        }
    }
    with patch.object(client.session, "get", return_value=_mock_get(data)):
        results = list(client.search_track("song"))

    assert len(results) == 1
    assert isinstance(results[0], Track)
    assert results[0].title == "Song"
    assert results[0].artist_id == 5


# ---------------------------------------------------------------------------
# search_artist
# ---------------------------------------------------------------------------

def test_search_artist(client):
    search_data = {"results": {"artists": [{"id": 3, "name": "The Band", "image": ""}]}}
    profile_data = {"albums": [], "tracks": [], "relatedTo": []}
    with patch.object(client.session, "get",
                      side_effect=[_mock_get(search_data), _mock_get(profile_data)]):
        results = list(client.search_artist("the band"))

    assert len(results) == 1
    assert isinstance(results[0], Artist)
    assert results[0].title == "The Band"


# ---------------------------------------------------------------------------
# search_playlist
# ---------------------------------------------------------------------------

def test_search_playlist(client):
    data = {
        "results": {
            "playlists": [{"id": 55, "name": "Chill Vibes", "description": "Relax",
                           "urls": {"web": "http://example.com",
                                    "image": "http://img.example.com"}}]
        }
    }
    with patch.object(client.session, "get", return_value=_mock_get(data)):
        results = list(client.search_playlist("chill"))

    assert len(results) == 1
    assert isinstance(results[0], Playlist)
    assert results[0].title == "Chill Vibes"
    assert results[0].url == "http://example.com"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_http_error_propagates(client):
    import requests
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.HTTPError("404")
    with patch.object(client.session, "get", return_value=mock_resp):
        with pytest.raises(requests.HTTPError):
            list(client.search_stations("anything"))


def test_empty_results(client):
    data = {"results": {"stations": []}}
    with patch.object(client.session, "get", return_value=_mock_get(data)):
        results = list(client.search_stations("nothing"))
    assert results == []


def test_parallel_skips_failed_detail(client):
    """A detail fetch that raises is skipped; other results still returned."""
    search_data = {
        "results": {
            "stations": [{"id": 1, "name": "Good FM"}, {"id": 2, "name": "Bad FM"}]
        }
    }
    good_station = {
        "hits": [{"streams": {"mp3": "http://stream.example.com/good"},
                  "logo": "", "description": ""}]
    }
    import requests as req

    call_count = 0
    lock = Lock()

    def side_effect(url, params=None, timeout=None):
        nonlocal call_count
        with lock:
            call_count += 1
            count = call_count
        if count == 1:
            return _mock_get(search_data)
        if "liveStation" in url and "/2" in url:
            bad = MagicMock()
            bad.raise_for_status.side_effect = req.HTTPError("500")
            return bad
        return _mock_get(good_station)

    with patch.object(client.session, "get", side_effect=side_effect):
        results = list(client.search_stations("fm"))

    assert len(results) == 1
    assert results[0].title == "Good FM"


# ---------------------------------------------------------------------------
# Constructor params
# ---------------------------------------------------------------------------

def test_custom_timeout_and_workers():
    c = IHeartRadio(timeout=3, max_workers=2)
    assert c.timeout == 3
    assert c.max_workers == 2
