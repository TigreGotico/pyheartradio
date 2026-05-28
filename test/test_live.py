"""Live integration tests — hit the real iHeartRadio API.

These are NOT run in the standard CI build (they require network access and
can flap if the API is unavailable). They run nightly via nightly-live.yml
and can be triggered manually.

Run locally:
    pytest test/test_live.py -v
"""
import pytest
from pyheartradio import IHeartRadio
from pyheartradio.models import Artist, Playlist, Podcast, PodcastEpisode, Station, Track

client = IHeartRadio(timeout=15)


def test_live_search_stations():
    results = list(client.search_stations("jazz", max_results=3))
    assert results, "expected at least one station"
    s = results[0]
    assert isinstance(s, Station)
    assert s.id
    assert s.title
    assert s.stream.startswith("http")


def test_live_search_podcast():
    results = list(client.search_podcast("Radiolab", max_results=3))
    assert results
    p = results[0]
    assert isinstance(p, Podcast)
    assert p.id
    assert p.title


def test_live_podcast_episodes():
    podcast = next(client.search_podcast("Radiolab"), None)
    assert podcast is not None
    episodes = list(client.get_podcast_episodes(podcast.id))
    assert episodes
    ep = episodes[0]
    assert isinstance(ep, PodcastEpisode)
    assert ep.podcast_id == podcast.id
    assert ep.stream.startswith("http")


def test_live_search_track():
    results = list(client.search_track("Bohemian Rhapsody", max_results=3))
    assert results
    t = results[0]
    assert isinstance(t, Track)
    assert t.id
    assert t.title


def test_live_search_artist():
    results = list(client.search_artist("David Bowie", max_results=2))
    assert results
    a = results[0]
    assert isinstance(a, Artist)
    assert a.id
    assert a.title


def test_live_search_playlist():
    results = list(client.search_playlist("workout", max_results=3))
    assert results
    pl = results[0]
    assert isinstance(pl, Playlist)
    assert pl.id
    assert pl.title


def test_live_to_external_ids_station():
    station = next(client.search_stations("jazz"), None)
    assert station is not None
    ids = station.to_external_ids()
    assert "iheart_station_id" in ids
    assert "stream_url" in ids


def test_live_max_results_respected():
    results = list(client.search_stations("rock", max_results=2))
    assert len(results) <= 2
