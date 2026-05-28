def test_import():
    from pyheartradio import IHeartRadio
    from pyheartradio.models import (
        Album, Artist, NowPlaying, Playlist, Podcast, PodcastEpisode,
        SearchResults, Station, Track,
    )


def test_version():
    from pyheartradio.version import __version__
    assert __version__


def test_instantiate():
    from pyheartradio import IHeartRadio
    client = IHeartRadio()
    assert client.timeout == 10
    assert client.session is not None
