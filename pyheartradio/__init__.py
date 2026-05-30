import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterator, List, Optional
import requests

from pyheartradio.models import (
    Album, Artist, NowPlaying, Playlist, Podcast, PodcastEpisode,
    SearchResults, Station, Track,
)

_DEFAULT_MAX_RESULTS = 10
_DEFAULT_MAX_WORKERS = 6

# Preferred stream format order — first match wins. Callers that need a
# specific format should inspect Station.streams directly.
_STREAM_FORMAT_PREFERENCE = (
    "shoutcast_stream",
    "secure_shoutcast_stream",
    "stw_stream",
    "mp3",
    "aac",
    "hls_stream",
)

LOG = logging.getLogger(__name__)


class IHeartRadio:
    """Client for the iHeartRadio public API.

    All search methods return iterators of typed dataclass instances.
    The client reuses a single :class:`requests.Session` across calls and
    fetches per-item detail URLs in parallel to minimise latency.

    Parameters
    ----------
    timeout:
        HTTP request timeout in seconds (default: 10).
    max_workers:
        Maximum threads for parallel detail fetches (default: 6).

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
    now_playing_url = "https://us.api.iheart.com/api/v3/live-meta/stream/{stream_id}/currentTrackMeta"
    artist_profile_url = "https://us.api.iheart.com/api/v3/artists/profiles/{artist_id}"
    artist_albums_url = "https://us.api.iheart.com/api/v3/catalog/artist/{artist_id}/albums"
    similar_artists_url = "https://us.api.iheart.com/api/v1/catalog/artist/{artist_id}/getSimilar"
    track_url = "https://us.api.iheart.com/api/v3/catalog/tracks/{track_id}"

    def __init__(self, timeout: int = 10, max_workers: int = _DEFAULT_MAX_WORKERS) -> None:
        self.timeout = timeout
        self.max_workers = max_workers
        try:
            from unblock_requests import CloudflareSession

            self.session = CloudflareSession(
                env_prefix="PYHEARTRADIO", wayback_fallback=True
            )
        except Exception:
            self.session = requests.Session()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, params: Optional[dict] = None) -> dict:
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _search_payload(self, keywords: str, max_results: int, **flags) -> dict:
        base: dict = {
            "keywords": keywords,
            "maxRows": max_results,
            "bundle": "false",
            "station": "false",
            "artist": "false",
            "track": "false",
            "playlist": "false",
            "podcast": "false",
        }
        base.update(flags)
        return base

    def _parallel(self, fn, items: list) -> List[tuple]:
        """Run ``fn(item)`` for each item in parallel; return (item, result) pairs
        in the original order. Items whose fetch raised are logged and skipped."""
        if not items:
            return []
        results: dict = {}
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(items))) as pool:
            futures = {pool.submit(fn, item): i for i, item in enumerate(items)}
            for fut in as_completed(futures):
                idx = futures[fut]
                exc = fut.exception()
                if exc is not None:
                    LOG.debug("parallel fetch failed for item %d: %s", idx, exc)
                else:
                    results[idx] = (items[idx], fut.result())
        return [results[i] for i in sorted(results)]

    @staticmethod
    def _pick_stream(streams: dict) -> str:
        """Return the preferred stream URL from a streams dict.

        Tries formats in :data:`_STREAM_FORMAT_PREFERENCE` order, then
        falls back to the first available entry. Returns ``""`` when the
        dict is empty.
        """
        for fmt in _STREAM_FORMAT_PREFERENCE:
            if fmt in streams:
                return streams[fmt]
        return next(iter(streams.values()), "")

    @staticmethod
    def _station_from_raw(raw: dict, hit: dict) -> Optional[Station]:
        streams = hit.get("streams") or {}
        if not streams:
            return None
        return Station(
            id=raw["id"],
            title=raw.get("name", ""),
            description=hit.get("description", ""),
            image=hit.get("logo", ""),
            stream=IHeartRadio._pick_stream(streams),
            streams=dict(streams),
        )

    @staticmethod
    def _hit_from_detail(res: dict) -> dict:
        """Safely extract the first hit dict from a station detail response.

        Returns ``{}`` when hits is absent *or* when the list is empty, so
        callers never receive an IndexError on a well-formed-but-empty response.
        """
        hits = res.get("hits") or []
        return hits[0] if hits else {}

    @staticmethod
    def _album_from_raw(raw: dict) -> Album:
        album_id: Optional[int] = raw.get("id") or raw.get("albumId") or None
        return Album(
            id=album_id,
            title=raw.get("title") or raw.get("albumName") or "",
            artist=raw.get("artistName") or raw.get("artist") or "",
            artist_id=raw.get("artistId"),
            year=raw.get("year") or raw.get("releaseYear"),
            image=raw.get("image") or raw.get("imageUrl") or "",
            track_count=raw.get("trackCount"),
        )

    # ------------------------------------------------------------------
    # Search methods
    # ------------------------------------------------------------------

    def search_stations(self, search_term: str,
                        max_results: int = _DEFAULT_MAX_RESULTS) -> Iterator[Station]:
        """Search for live radio stations.

        Yields one :class:`~pyheartradio.models.Station` per result that
        has at least one playable stream URL. Detail URLs are fetched in
        parallel. Each station carries all available stream formats in
        :attr:`~pyheartradio.models.Station.streams`.

        Parameters
        ----------
        search_term:
            Free-text query, e.g. ``"classic rock"`` or ``"WNYC"``.
        max_results:
            Maximum number of search results to request (default: 10).
        """
        data = self._get(self.search_url,
                         self._search_payload(search_term, max_results, station="true"))
        raws = data.get("results", {}).get("stations", [])

        def fetch(raw: dict) -> dict:
            return self._get(self.station_stream_url.format(stream_id=raw["id"]))

        for raw, res in self._parallel(fetch, raws):
            hit = self._hit_from_detail(res)
            station = self._station_from_raw(raw, hit)
            if station:
                yield station

    def search_podcast(self, search_term: str,
                       max_results: int = _DEFAULT_MAX_RESULTS) -> Iterator[Podcast]:
        """Search for podcast shows.

        Parameters
        ----------
        search_term:
            Free-text query, e.g. ``"true crime"`` or ``"Radiolab"``.
        max_results:
            Maximum number of search results to request (default: 10).
        """
        data = self._get(self.search_url,
                         self._search_payload(search_term, max_results, podcast="true"))
        for raw in data.get("results", {}).get("podcasts", []):
            yield Podcast(
                id=raw["id"],
                title=raw.get("title", ""),
                description=raw.get("description", ""),
                image=raw.get("image", ""),
            )

    def search_track(self, search_term: str,
                     max_results: int = _DEFAULT_MAX_RESULTS) -> Iterator[Track]:
        """Search for music tracks.

        .. note::
            iHeartRadio does not expose stream URLs for individual tracks
            via the public API.  Use :meth:`search_stations` or
            :meth:`search_artist` for playable content.

        Parameters
        ----------
        search_term:
            Free-text query, e.g. ``"Bohemian Rhapsody"``.
        max_results:
            Maximum number of search results to request (default: 10).
        """
        data = self._get(self.search_url,
                         self._search_payload(search_term, max_results, track="true"))
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

    def search_artist(self, search_term: str,
                      max_results: int = _DEFAULT_MAX_RESULTS) -> Iterator[Artist]:
        """Search for artists, with full profile data fetched in parallel.

        Parameters
        ----------
        search_term:
            Free-text query, e.g. ``"David Bowie"``.
        max_results:
            Maximum number of search results to request (default: 10).
        """
        data = self._get(self.search_url,
                         self._search_payload(search_term, max_results, artist="true"))
        raws = data.get("results", {}).get("artists", [])

        def fetch(raw: dict) -> dict:
            return self._get(self.artist_profile_url.format(artist_id=raw["id"]))

        for raw, profile in self._parallel(fetch, raws):
            yield Artist(
                id=raw["id"],
                title=raw.get("name", ""),
                image=raw.get("image", ""),
                albums=profile.get("albums", []),
                tracks=profile.get("tracks", []),
                related_artists=profile.get("relatedTo", []),
            )

    def search_playlist(self, search_term: str,
                        max_results: int = _DEFAULT_MAX_RESULTS) -> Iterator[Playlist]:
        """Search for curated playlists.

        Parameters
        ----------
        search_term:
            Free-text query, e.g. ``"workout"`` or ``"90s hits"``.
        max_results:
            Maximum number of search results to request (default: 10).
        """
        data = self._get(self.search_url,
                         self._search_payload(search_term, max_results, playlist="true"))
        for raw in data.get("results", {}).get("playlists", []):
            urls = raw.get("urls", {})
            yield Playlist(
                id=raw["id"],
                title=raw.get("name", ""),
                description=raw.get("description", ""),
                image=urls.get("image", ""),
                url=urls.get("web", ""),
            )

    def search(self, query: str,
               max_results: int = _DEFAULT_MAX_RESULTS) -> SearchResults:
        """Unified search across all entity types in a single API call.

        Returns a :class:`~pyheartradio.models.SearchResults` with all entity
        types populated. Station stream URLs are fetched in parallel.

        .. note::
            Artist results from this method are stubs (id, title, image only).
            Use :meth:`search_artist` to receive fully-populated Artist objects
            with albums, tracks, and related artists.

        Parameters
        ----------
        query:
            Free-text query.
        max_results:
            Maximum results per entity type (default: 10).

        Example
        -------
        >>> results = client.search("jazz")
        >>> print(len(results.stations), "stations,", len(results.podcasts), "podcasts")
        """
        data = self._get(self.search_url,
                         self._search_payload(query, max_results,
                                              station="true", artist="true",
                                              track="true", playlist="true",
                                              podcast="true"))
        res = data.get("results", {})

        station_raws = res.get("stations", [])

        def fetch_station(raw: dict) -> dict:
            return self._get(self.station_stream_url.format(stream_id=raw["id"]))

        stations: List[Station] = []
        for raw, hit_res in self._parallel(fetch_station, station_raws):
            hit = self._hit_from_detail(hit_res)
            station = self._station_from_raw(raw, hit)
            if station:
                stations.append(station)

        podcasts = [
            Podcast(id=r["id"], title=r.get("title", ""),
                    description=r.get("description", ""), image=r.get("image", ""))
            for r in res.get("podcasts", [])
        ]
        artists = [
            Artist(id=r["id"], title=r.get("name", ""), image=r.get("image", ""))
            for r in res.get("artists", [])
        ]
        tracks = [
            Track(id=r["id"], title=r.get("title", ""),
                  artist=r.get("artistName", ""), album=r.get("albumName", ""),
                  image=r.get("image", ""), artist_id=r.get("artistId"),
                  album_id=r.get("albumId"))
            for r in res.get("tracks", [])
        ]
        playlists = [
            Playlist(id=r["id"], title=r.get("name", ""),
                     description=r.get("description", ""),
                     image=r.get("urls", {}).get("image", ""),
                     url=r.get("urls", {}).get("web", ""))
            for r in res.get("playlists", [])
        ]

        return SearchResults(query=query, stations=stations, podcasts=podcasts,
                             artists=artists, tracks=tracks, playlists=playlists)

    # ------------------------------------------------------------------
    # Direct lookup methods
    # ------------------------------------------------------------------

    def get_now_playing(self, station_id: int) -> NowPlaying:
        """Return what is currently on air for a live station.

        Parameters
        ----------
        station_id:
            The numeric iHeartRadio station ID from a
            :meth:`search_stations` result.

        Example
        -------
        >>> station = next(client.search_stations("WNYC"))
        >>> np = client.get_now_playing(station.id)
        >>> print(np.artist, "—", np.title)
        """
        data = self._get(self.now_playing_url.format(stream_id=station_id))
        # Use explicit key lookup — do not use or-chaining on dicts because
        # an empty dict {} is falsy and would incorrectly fall through to the
        # next key when the station is between tracks.
        track = data.get("currentTrack")
        if not isinstance(track, dict):
            track = data.get("track")
        if not isinstance(track, dict):
            track = {}
        return NowPlaying(
            station_id=station_id,
            title=track.get("title") or track.get("trackTitle") or "",
            artist=track.get("artist") or track.get("artistName") or "",
            album=track.get("album") or track.get("albumName") or "",
            image=track.get("image") or track.get("imageUrl") or "",
            duration=track.get("duration"),
        )

    def get_podcast_episodes(self, podcast_id: int) -> Iterator[PodcastEpisode]:
        """Retrieve episodes for a specific podcast.

        Stream URL lookups run in parallel.

        Parameters
        ----------
        podcast_id:
            The numeric iHeartRadio podcast ID from a
            :meth:`search_podcast` result.
        """
        res = self._get(self.podcast_episodes_url.format(podcast_id=podcast_id))
        raws = res.get("data", [])

        def fetch(raw: dict) -> dict:
            return self._get(self.podcast_stream_url.format(episode_id=raw["id"]))

        for raw, stream_res in self._parallel(fetch, raws):
            yield PodcastEpisode(
                id=raw["id"],
                podcast_id=podcast_id,
                title=raw.get("title", ""),
                description=raw.get("description", ""),
                image=raw.get("imageUrl", ""),
                duration=raw.get("duration"),
                stream=stream_res.get("episode", {}).get("mediaUrl", ""),
            )

    def get_track(self, track_id: int) -> Track:
        """Fetch a track by its iHeartRadio ID.

        Parameters
        ----------
        track_id:
            The numeric iHeartRadio track ID.
        """
        data = self._get(self.track_url.format(track_id=track_id))
        # Use explicit None check — do not use or-chaining because a present
        # but null/empty 'track' key should not fall back to the envelope dict.
        raw = data.get("track")
        if not isinstance(raw, dict):
            raw = data
        return Track(
            id=raw.get("id") or track_id,
            title=raw.get("title") or raw.get("trackTitle") or "",
            artist=raw.get("artistName") or raw.get("artist") or "",
            album=raw.get("albumName") or raw.get("album") or "",
            image=raw.get("image") or raw.get("imageUrl") or "",
            artist_id=raw.get("artistId"),
            album_id=raw.get("albumId"),
        )

    def get_artist_albums(self, artist_id: int) -> Iterator[Album]:
        """Fetch albums for a known artist ID without a full profile fetch.

        Parameters
        ----------
        artist_id:
            The numeric iHeartRadio artist ID from a
            :meth:`search_artist` result.
        """
        data = self._get(self.artist_albums_url.format(artist_id=artist_id))
        for raw in data.get("albums") or data.get("data") or []:
            yield self._album_from_raw(raw)

    def get_similar_artists(self, artist_id: int) -> Iterator[Artist]:
        """Fetch artists similar to a given artist ID.

        Parameters
        ----------
        artist_id:
            The numeric iHeartRadio artist ID.
        """
        data = self._get(self.similar_artists_url.format(artist_id=artist_id))
        for raw in data.get("artists") or data.get("data") or []:
            yield Artist(
                id=raw.get("id") or raw.get("artistId") or 0,
                title=raw.get("name") or raw.get("artistName") or "",
                image=raw.get("image") or raw.get("imageUrl") or "",
            )
