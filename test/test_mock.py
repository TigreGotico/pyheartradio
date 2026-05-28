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


def test_search_stations(client):
    search_data = {"results": {"stations": [{"id": 1, "name": "Rock FM"}]}}
    station_data = {
        "hits": [{"streams": {"shoutcast_stream": "http://stream.example.com"},
                  "logo": "http://img.example.com",
                  "description": "Best rock"}]
    }
    with patch.object(client.session, "get", side_effect=[_mock_get(search_data), _mock_get(station_data)]):
        results = list(client.search_stations("rock"))

    assert len(results) == 1
    assert isinstance(results[0], Station)
    assert results[0].title == "Rock FM"
    assert results[0].stream == "http://stream.example.com"
    assert results[0].id == 1


def test_search_stations_no_streams_skipped(client):
    search_data = {"results": {"stations": [{"id": 1, "name": "Silent FM"}]}}
    station_data = {"hits": [{"streams": {}, "logo": "", "description": ""}]}
    with patch.object(client.session, "get", side_effect=[_mock_get(search_data), _mock_get(station_data)]):
        results = list(client.search_stations("silent"))
    assert results == []


def test_search_podcast(client):
    data = {
        "results": {
            "podcasts": [{"id": 42, "title": "Tech Talk", "image": "http://img.example.com", "description": "Tech news"}]
        }
    }
    with patch.object(client.session, "get", return_value=_mock_get(data)):
        results = list(client.search_podcast("tech"))

    assert len(results) == 1
    assert isinstance(results[0], Podcast)
    assert results[0].title == "Tech Talk"
    assert results[0].id == 42


def test_get_podcast_episodes(client):
    episodes_data = {
        "data": [{"id": 7, "title": "Episode 1", "duration": 1800,
                  "description": "Intro", "imageUrl": "http://img.example.com"}]
    }
    stream_data = {"episode": {"mediaUrl": "http://media.example.com/ep1.mp3"}}
    with patch.object(client.session, "get", side_effect=[_mock_get(episodes_data), _mock_get(stream_data)]):
        results = list(client.get_podcast_episodes(42))

    assert len(results) == 1
    assert isinstance(results[0], PodcastEpisode)
    assert results[0].stream == "http://media.example.com/ep1.mp3"
    assert results[0].duration == 1800
    assert results[0].podcast_id == 42


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


def test_search_artist(client):
    search_data = {"results": {"artists": [{"id": 3, "name": "The Band", "image": ""}]}}
    profile_data = {"albums": [], "tracks": [], "relatedTo": []}
    with patch.object(client.session, "get", side_effect=[_mock_get(search_data), _mock_get(profile_data)]):
        results = list(client.search_artist("the band"))

    assert len(results) == 1
    assert isinstance(results[0], Artist)
    assert results[0].title == "The Band"


def test_search_playlist(client):
    data = {
        "results": {
            "playlists": [{"id": 55, "name": "Chill Vibes", "description": "Relax",
                           "urls": {"web": "http://example.com", "image": "http://img.example.com"}}]
        }
    }
    with patch.object(client.session, "get", return_value=_mock_get(data)):
        results = list(client.search_playlist("chill"))

    assert len(results) == 1
    assert isinstance(results[0], Playlist)
    assert results[0].title == "Chill Vibes"
    assert results[0].url == "http://example.com"


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
