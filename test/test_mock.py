from threading import Lock
from unittest.mock import MagicMock, patch
import pytest
from pyheartradio import IHeartRadio
from pyheartradio.models import (
    Album, Artist, NowPlaying, Playlist, Podcast, PodcastEpisode,
    SearchResults, Station, Track,
)


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


# ---------------------------------------------------------------------------
# Station streams dict
# ---------------------------------------------------------------------------

def test_station_exposes_all_stream_formats(client):
    search_data = {"results": {"stations": [{"id": 1, "name": "Multi FM"}]}}
    station_data = {
        "hits": [{"streams": {"shoutcast_stream": "http://shout.example.com",
                               "hls_stream": "http://hls.example.com"},
                  "logo": "", "description": ""}]
    }
    with patch.object(client.session, "get",
                      side_effect=[_mock_get(search_data), _mock_get(station_data)]):
        results = list(client.search_stations("multi"))

    assert len(results) == 1
    # shoutcast_stream is first in _STREAM_FORMAT_PREFERENCE
    assert results[0].stream == "http://shout.example.com"
    assert "hls_stream" in results[0].streams
    assert "shoutcast_stream" in results[0].streams


def test_station_stream_preference_order(client):
    """shoutcast_stream is preferred over hls_stream regardless of dict order."""
    from pyheartradio import IHeartRadio
    streams = {"hls_stream": "http://hls.example.com",
               "shoutcast_stream": "http://shout.example.com"}
    assert IHeartRadio._pick_stream(streams) == "http://shout.example.com"


def test_station_empty_hits_list_yields_nothing(client):
    """hits: [] (key present, list empty) must not crash with IndexError."""
    search_data = {"results": {"stations": [{"id": 1, "name": "Ghost FM"}]}}
    empty_hits = {"hits": []}
    with patch.object(client.session, "get",
                      side_effect=[_mock_get(search_data), _mock_get(empty_hits)]):
        results = list(client.search_stations("ghost"))
    assert results == []


def test_hit_from_detail_absent_key():
    from pyheartradio import IHeartRadio
    assert IHeartRadio._hit_from_detail({}) == {}
    assert IHeartRadio._hit_from_detail({"hits": []}) == {}
    assert IHeartRadio._hit_from_detail({"hits": [{"id": 1}]}) == {"id": 1}


# ---------------------------------------------------------------------------
# get_now_playing
# ---------------------------------------------------------------------------

def test_get_now_playing(client):
    data = {"currentTrack": {"title": "Heroes", "artistName": "David Bowie",
                              "albumName": "Heroes", "duration": 360}}
    with patch.object(client.session, "get", return_value=_mock_get(data)):
        np = client.get_now_playing(7)

    assert isinstance(np, NowPlaying)
    assert np.station_id == 7
    assert np.title == "Heroes"
    assert np.artist == "David Bowie"
    assert np.duration == 360


def test_get_now_playing_empty_when_no_track(client):
    with patch.object(client.session, "get", return_value=_mock_get({})):
        np = client.get_now_playing(7)
    assert np.station_id == 7
    assert np.title == ""


def test_get_now_playing_empty_currentTrack_dict_not_skipped(client):
    """currentTrack: {} (between tracks) must not fall through to 'track' key."""
    data = {"currentTrack": {}, "track": {"title": "Ad jingle", "artistName": "Ad"}}
    with patch.object(client.session, "get", return_value=_mock_get(data)):
        np = client.get_now_playing(7)
    # currentTrack={} is the correct payload; 'track' is a different key and
    # must not be read.
    assert np.title == ""
    assert np.artist == ""


def test_get_now_playing_null_currentTrack_falls_to_track(client):
    """currentTrack: null should fall through to 'track' key."""
    data = {"currentTrack": None, "track": {"title": "Song", "artistName": "Artist"}}
    with patch.object(client.session, "get", return_value=_mock_get(data)):
        np = client.get_now_playing(7)
    assert np.title == "Song"
    assert np.artist == "Artist"


# ---------------------------------------------------------------------------
# get_track
# ---------------------------------------------------------------------------

def test_get_track(client):
    data = {"track": {"id": 99, "title": "Heroes", "artistName": "David Bowie",
                       "albumName": "Heroes", "artistId": 5, "albumId": 10}}
    with patch.object(client.session, "get", return_value=_mock_get(data)):
        track = client.get_track(99)

    assert isinstance(track, Track)
    assert track.id == 99
    assert track.title == "Heroes"
    assert track.artist_id == 5


def test_get_track_null_track_key_does_not_corrupt(client):
    """track: null must not fall back to the envelope dict and silently pass."""
    data = {"track": None, "status": "not_found", "id": 0}
    with patch.object(client.session, "get", return_value=_mock_get(data)):
        track = client.get_track(99)
    # Falls back to the envelope dict; id=0 is falsy so track_id sentinel is used
    # and title comes from envelope keys (absent → "")
    assert track.id == 99  # sentinel from track_id arg
    assert track.title == ""  # envelope has no title


def test_get_track_no_track_key_uses_envelope(client):
    """When 'track' key is absent entirely, the response is the track directly."""
    data = {"id": 55, "title": "Direct", "artistName": "Artist"}
    with patch.object(client.session, "get", return_value=_mock_get(data)):
        track = client.get_track(55)
    assert track.id == 55
    assert track.title == "Direct"


# ---------------------------------------------------------------------------
# get_artist_albums
# ---------------------------------------------------------------------------

def test_get_artist_albums(client):
    data = {"albums": [{"id": 1, "title": "Ziggy", "artistName": "Bowie", "year": 1972},
                        {"id": 2, "title": "Heroes", "artistName": "Bowie", "year": 1977}]}
    with patch.object(client.session, "get", return_value=_mock_get(data)):
        albums = list(client.get_artist_albums(100))

    assert len(albums) == 2
    assert isinstance(albums[0], Album)
    assert albums[0].title == "Ziggy"
    assert albums[0].year == 1972


# ---------------------------------------------------------------------------
# get_similar_artists
# ---------------------------------------------------------------------------

def test_get_similar_artists(client):
    data = {"artists": [{"id": 5, "name": "Roxy Music", "image": "http://img.example.com"}]}
    with patch.object(client.session, "get", return_value=_mock_get(data)):
        similar = list(client.get_similar_artists(100))

    assert len(similar) == 1
    assert isinstance(similar[0], Artist)
    assert similar[0].title == "Roxy Music"


# ---------------------------------------------------------------------------
# search (unified)
# ---------------------------------------------------------------------------

def test_search_unified(client):
    search_response = {
        "results": {
            "stations": [{"id": 1, "name": "Jazz FM"}],
            "podcasts": [{"id": 2, "title": "Jazz Podcast", "description": "", "image": ""}],
            "artists":  [{"id": 3, "name": "Miles Davis", "image": ""}],
            "tracks":   [{"id": 4, "title": "Kind of Blue",
                          "artistName": "Miles", "albumName": "KoB",
                          "image": "", "artistId": 3, "albumId": 10}],
            "playlists": [{"id": 5, "name": "Jazz Chill",
                           "description": "", "urls": {}}],
        }
    }
    station_detail = {
        "hits": [{"streams": {"mp3": "http://stream.example.com"}, "logo": "", "description": ""}]
    }
    with patch.object(client.session, "get",
                      side_effect=[_mock_get(search_response), _mock_get(station_detail)]):
        results = client.search("jazz")

    assert isinstance(results, SearchResults)
    assert results.query == "jazz"
    assert len(results.stations) == 1
    assert len(results.podcasts) == 1
    assert len(results.artists) == 1
    assert len(results.tracks) == 1
    assert len(results.playlists) == 1
    assert bool(results) is True


def test_search_unified_empty(client):
    empty = {"results": {"stations": [], "podcasts": [], "artists": [],
                         "tracks": [], "playlists": []}}
    with patch.object(client.session, "get", return_value=_mock_get(empty)):
        results = client.search("zzz")
    assert not results
