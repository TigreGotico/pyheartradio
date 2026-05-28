from dataclasses import asdict
from pyheartradio.models import (
    Album, Artist, NowPlaying, Playlist, Podcast, PodcastEpisode,
    SearchResults, Station, Track,
)


def test_station_external_ids():
    s = Station(id=7, title="Jazz FM", stream="http://stream.example.com/jazz")
    ids = s.to_external_ids()
    assert ids["iheart_station_id"] == "7"
    assert ids["stream_url"] == "http://stream.example.com/jazz"


def test_station_no_stream_omits_stream_url():
    s = Station(id=7, title="Jazz FM")
    assert "stream_url" not in s.to_external_ids()


def test_station_signals():
    s = Station(id=7, title="Jazz FM")
    sig = s.to_signals()
    assert sig["title"] == "Jazz FM"
    assert sig["medium"] == "radio"


def test_station_streams_dict():
    s = Station(id=7, title="X", stream="http://mp3.example.com",
                streams={"mp3": "http://mp3.example.com", "hls": "http://hls.example.com"})
    assert len(s.streams) == 2
    assert s.streams["hls"] == "http://hls.example.com"
    # stream is still the convenience first-URL field
    assert s.stream == "http://mp3.example.com"


def test_now_playing_to_signals():
    np = NowPlaying(station_id=1, title="Heroes", artist="David Bowie",
                    album="Heroes", duration=360)
    sig = np.to_signals()
    assert sig["title"] == "Heroes"
    assert sig["artist"] == "David Bowie"
    assert sig["duration"] == 360
    assert sig["medium"] == "music"


def test_now_playing_to_signals_empty_title_omitted():
    np = NowPlaying(station_id=1)
    sig = np.to_signals()
    assert "title" not in sig


def test_now_playing_external_ids():
    np = NowPlaying(station_id=42)
    assert np.to_external_ids() == {"iheart_station_id": "42"}


def test_album_external_ids():
    a = Album(id=10, title="Ziggy", artist_id=100)
    ids = a.to_external_ids()
    assert ids["iheart_album_id"] == "10"
    assert ids["iheart_artist_id"] == "100"


def test_album_signals():
    a = Album(id=10, title="Ziggy", artist="David Bowie", year=1972)
    sig = a.to_signals()
    assert sig["title"] == "Ziggy"
    assert sig["artist"] == "David Bowie"
    assert sig["year"] == 1972
    assert sig["medium"] == "music"


def test_podcast_external_ids():
    p = Podcast(id=42, title="Radiolab")
    assert p.to_external_ids() == {"iheart_podcast_id": "42"}


def test_podcast_episode_external_ids_all_keys():
    ep = PodcastEpisode(id=9, podcast_id=42, title="Ep",
                        stream="http://audio.example.com/ep9.mp3")
    ids = ep.to_external_ids()
    assert ids["iheart_episode_id"] == "9"
    assert ids["iheart_podcast_id"] == "42"
    assert ids["stream_url"] == "http://audio.example.com/ep9.mp3"


def test_podcast_episode_signals_with_duration():
    ep = PodcastEpisode(id=9, title="Ep", duration=1800)
    sig = ep.to_signals()
    assert sig["duration"] == 1800
    assert sig["medium"] == "podcast"


def test_podcast_episode_signals_without_duration():
    ep = PodcastEpisode(id=9, title="Ep")
    assert "duration" not in ep.to_signals()


def test_track_external_ids():
    t = Track(id=5, title="Heroes", artist_id=100)
    ids = t.to_external_ids()
    assert ids["iheart_track_id"] == "5"
    assert ids["iheart_artist_id"] == "100"


def test_track_signals_with_artist_album():
    t = Track(id=5, title="Heroes", artist="David Bowie", album="Heroes")
    sig = t.to_signals()
    assert sig["artist"] == "David Bowie"
    assert sig["album"] == "Heroes"
    assert sig["medium"] == "music"


def test_track_signals_empty_artist_omitted():
    t = Track(id=5, title="Heroes")
    assert "artist" not in t.to_signals()
    assert "album" not in t.to_signals()


def test_artist_external_ids():
    a = Artist(id=1, title="The Beatles")
    assert a.to_external_ids() == {"iheart_artist_id": "1"}


def test_playlist_external_ids():
    p = Playlist(id=99, title="Chill")
    assert p.to_external_ids() == {"iheart_playlist_id": "99"}


def test_search_results_bool():
    empty = SearchResults(query="x")
    assert not empty
    with_data = SearchResults(query="x", stations=[Station(id=1, title="X")])
    assert with_data


def test_asdict_works_on_all_models():
    for model in [
        Station(id=1, title="X"),
        NowPlaying(station_id=2),
        Album(id=3, title="Y"),
        Podcast(id=4, title="Z"),
        PodcastEpisode(id=5, title="W"),
        Track(id=6, title="V"),
        Artist(id=7, title="A"),
        Playlist(id=8, title="B"),
    ]:
        d = asdict(model)
        assert isinstance(d, dict)
        assert "id" in d or "station_id" in d
