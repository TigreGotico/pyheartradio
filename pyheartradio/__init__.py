from typing import Iterator, Optional
import requests

from pyheartradio.models import Artist, Playlist, Podcast, PodcastEpisode, Station, Track


class IHeartRadio:
    """Client for the iHeartRadio public API.

    All search methods return iterators of typed dataclass instances.
    The client reuses a single :class:`requests.Session` across calls.

    Parameters
    ----------
    timeout:
        HTTP request timeout in seconds (default: 10).

    Example
    -------
    >>> client = IHeartRadio()
    >>> for station in client.search_stations("classic rock"):
    ...     print(station.title, station.stream)
    """

    search_url = "https://us.api.iheart.com/api/v3/search/all"
    podcast_episodes_url = "https://us.api.iheart.com/api/v3/podcast/podcasts/{podcast_id}/episodes"
    podcast_stream_url = "https://us.api.iheart.com/api/v3/podcast/episodes/{episode_id}"
    station_stream_url = "https://us.api.iheart.com/api/v2/content/liveStations/{stream_id}"
    artist_profile_url = "https://us.api.iheart.com/api/v3/artists/profiles/{artist_id}"

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, params: Optional[dict] = None) -> dict:
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _search_payload(self, keywords: str, **flags) -> dict:
        base: dict = {
            "keywords": keywords,
            "maxRows": 10,
            "bundle": "false",
            "station": "false",
            "artist": "false",
            "track": "false",
            "playlist": "false",
            "podcast": "false",
        }
        base.update(flags)
        return base

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_stations(self, search_term: str) -> Iterator[Station]:
        """Search for live radio stations.

        Yields one :class:`~pyheartradio.models.Station` per result that
        has at least one playable stream URL.

        Parameters
        ----------
        search_term:
            Free-text query, e.g. ``"classic rock"`` or ``"WNYC"``.

        Example
        -------
        >>> for station in client.search_stations("jazz"):
        ...     print(station.title, "→", station.stream)
        """
        data = self._get(self.search_url, self._search_payload(search_term, station="true"))
        for raw in data.get("results", {}).get("stations", []):
            station_id = raw["id"]
            res = self._get(self.station_stream_url.format(stream_id=station_id))
            hit = res.get("hits", [{}])[0]
            streams = hit.get("streams", {})
            stream_url = next(iter(streams.values()), None)
            if stream_url:
                yield Station(
                    id=station_id,
                    title=raw.get("name", ""),
                    description=hit.get("description", ""),
                    image=hit.get("logo", ""),
                    stream=stream_url,
                )

    def search_podcast(self, search_term: str) -> Iterator[Podcast]:
        """Search for podcast shows.

        Yields one :class:`~pyheartradio.models.Podcast` per result.
        To retrieve individual episodes, pass the podcast
        :attr:`~pyheartradio.models.Podcast.id` to
        :meth:`get_podcast_episodes`.

        Parameters
        ----------
        search_term:
            Free-text query, e.g. ``"true crime"`` or ``"Radiolab"``.
        """
        data = self._get(self.search_url, self._search_payload(search_term, podcast="true"))
        for raw in data.get("results", {}).get("podcasts", []):
            yield Podcast(
                id=raw["id"],
                title=raw.get("title", ""),
                description=raw.get("description", ""),
                image=raw.get("image", ""),
            )

    def get_podcast_episodes(self, podcast_id: int) -> Iterator[PodcastEpisode]:
        """Retrieve episodes for a specific podcast.

        Each yielded :class:`~pyheartradio.models.PodcastEpisode` includes a
        direct audio stream URL.

        Parameters
        ----------
        podcast_id:
            The numeric iHeartRadio podcast ID — use the
            :attr:`~pyheartradio.models.Podcast.id` from a
            :meth:`search_podcast` result.

        Example
        -------
        >>> podcast = next(client.search_podcast("Serial"))
        >>> for ep in client.get_podcast_episodes(podcast.id):
        ...     print(ep.title, ep.stream)
        """
        res = self._get(self.podcast_episodes_url.format(podcast_id=podcast_id))
        for raw in res.get("data", []):
            episode_id = raw["id"]
            stream_res = self._get(self.podcast_stream_url.format(episode_id=episode_id))
            yield PodcastEpisode(
                id=episode_id,
                podcast_id=podcast_id,
                title=raw.get("title", ""),
                description=raw.get("description", ""),
                image=raw.get("imageUrl", ""),
                duration=raw.get("duration"),
                stream=stream_res.get("episode", {}).get("mediaUrl", ""),
            )

    def search_track(self, search_term: str) -> Iterator[Track]:
        """Search for music tracks.

        .. note::
            iHeartRadio does not expose stream URLs for individual tracks
            via the public API.  Use :meth:`search_stations` or
            :meth:`search_artist` for playable content.

        Parameters
        ----------
        search_term:
            Free-text query, e.g. ``"Bohemian Rhapsody"``.
        """
        data = self._get(self.search_url, self._search_payload(search_term, track="true"))
        for raw in data.get("results", {}).get("tracks", []):
            yield Track(
                id=raw["id"],
                title=raw.get("title", ""),
                artist=raw.get("artistName", ""),
                album=raw.get("albumName", ""),
                image=raw.get("image", ""),
                artist_id=raw.get("artistId"),
                album_id=raw.get("albumId"),
            )

    def search_artist(self, search_term: str) -> Iterator[Artist]:
        """Search for artists.

        Yields one :class:`~pyheartradio.models.Artist` per result, with
        albums, top tracks, and related artists populated from the artist
        profile endpoint.

        Parameters
        ----------
        search_term:
            Free-text query, e.g. ``"David Bowie"``.
        """
        data = self._get(self.search_url, self._search_payload(search_term, artist="true"))
        for raw in data.get("results", {}).get("artists", []):
            artist_id = raw["id"]
            profile = self._get(self.artist_profile_url.format(artist_id=artist_id))
            yield Artist(
                id=artist_id,
                title=raw.get("name", ""),
                image=raw.get("image", ""),
                albums=profile.get("albums", []),
                tracks=profile.get("tracks", []),
                related_artists=profile.get("relatedTo", []),
            )

    def search_playlist(self, search_term: str) -> Iterator[Playlist]:
        """Search for curated playlists.

        Parameters
        ----------
        search_term:
            Free-text query, e.g. ``"workout"`` or ``"90s hits"``.
        """
        data = self._get(self.search_url, self._search_payload(search_term, playlist="true"))
        for raw in data.get("results", {}).get("playlists", []):
            urls = raw.get("urls", {})
            yield Playlist(
                id=raw["id"],
                title=raw.get("name", ""),
                description=raw.get("description", ""),
                image=urls.get("image", ""),
                url=urls.get("web", ""),
            )
