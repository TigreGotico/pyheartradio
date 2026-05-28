"""Typed data models for iHeartRadio API responses.

Every model is a plain :mod:`dataclasses` dataclass — no runtime
dependencies beyond the standard library.  Two optional integration
helpers are provided on every model:

- :meth:`to_external_ids` — returns a ``Dict[str, str]`` that can be
  passed directly to :class:`mediavocab.models.ExternalIds.from_dict`.
  iHeartRadio IDs land in ``extra``; when a stream URL is present it is
  stored under the ``stream_url`` key so that
  ``ExternalIds.streams`` surfaces it as a playable
  ``Stream(platform="radio")`` entry.

- :meth:`to_signals` — returns a ``Dict[str, Any]`` compatible with
  the :class:`mediavocab.models.signals.Signals` constructor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Station
# ---------------------------------------------------------------------------

@dataclass
class Station:
    """A live radio station.

    ``stream`` holds the first available stream URL (backwards compatible).
    ``streams`` holds all available formats keyed by format name
    (e.g. ``{"shoutcast_stream": "http://…", "hls_stream": "http://…"}``)
    so callers can select a preferred format.
    """

    id: int
    title: str
    description: str = ""
    image: str = ""
    stream: str = ""
    streams: Dict[str, str] = field(default_factory=dict)

    def to_external_ids(self) -> Dict[str, str]:
        """External IDs dict compatible with ``ExternalIds.from_dict()``.

        Sets ``iheart_station_id`` and, when a stream URL is present,
        ``stream_url`` so that ``ExternalIds.streams`` returns a playable
        entry with ``platform="radio"``.
        """
        out: Dict[str, str] = {"iheart_station_id": str(self.id)}
        if self.stream:
            out["stream_url"] = self.stream
        return out

    def to_signals(self) -> Dict[str, Any]:
        """Signals dict compatible with ``Signals(**station.to_signals())``."""
        return {"title": self.title, "medium": "radio"}


# ---------------------------------------------------------------------------
# NowPlaying
# ---------------------------------------------------------------------------

@dataclass
class NowPlaying:
    """What is currently on air for a live station.

    Returned by :meth:`~pyheartradio.IHeartRadio.get_now_playing`.
    All fields except ``station_id`` may be empty when the station
    does not broadcast now-playing metadata.
    """

    station_id: int
    title: str = ""
    artist: str = ""
    album: str = ""
    image: str = ""
    duration: Optional[int] = None  # seconds

    def to_signals(self) -> Dict[str, Any]:
        sig: Dict[str, Any] = {"medium": "music"}
        if self.title:
            sig["title"] = self.title
        if self.artist:
            sig["artist"] = self.artist
        if self.album:
            sig["album"] = self.album
        if self.duration is not None:
            sig["duration"] = self.duration
        return sig

    def to_external_ids(self) -> Dict[str, str]:
        return {"iheart_station_id": str(self.station_id)}


# ---------------------------------------------------------------------------
# Album
# ---------------------------------------------------------------------------

@dataclass
class Album:
    """A music album.

    ``id`` is ``None`` when the API did not return an identifier for this
    album entry (e.g. partial data from an artist profile).
    """

    id: Optional[int]
    title: str
    artist: str = ""
    artist_id: Optional[int] = None
    year: Optional[int] = None
    image: str = ""
    track_count: Optional[int] = None

    def to_external_ids(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        if self.id is not None:
            out["iheart_album_id"] = str(self.id)
        if self.artist_id is not None:
            out["iheart_artist_id"] = str(self.artist_id)
        return out

    def to_signals(self) -> Dict[str, Any]:
        sig: Dict[str, Any] = {"title": self.title, "medium": "music"}
        if self.artist:
            sig["artist"] = self.artist
        if self.year:
            sig["year"] = self.year
        return sig


# ---------------------------------------------------------------------------
# Podcast
# ---------------------------------------------------------------------------

@dataclass
class Podcast:
    """A podcast show."""

    id: int
    title: str
    description: str = ""
    image: str = ""

    def to_external_ids(self) -> Dict[str, str]:
        return {"iheart_podcast_id": str(self.id)}

    def to_signals(self) -> Dict[str, Any]:
        return {"title": self.title, "medium": "podcast"}


# ---------------------------------------------------------------------------
# PodcastEpisode
# ---------------------------------------------------------------------------

@dataclass
class PodcastEpisode:
    """A single episode of a podcast."""

    id: int
    title: str
    podcast_id: Optional[int] = None
    description: str = ""
    image: str = ""
    duration: Optional[int] = None
    stream: str = ""

    def to_external_ids(self) -> Dict[str, str]:
        out: Dict[str, str] = {"iheart_episode_id": str(self.id)}
        if self.podcast_id is not None:
            out["iheart_podcast_id"] = str(self.podcast_id)
        if self.stream:
            out["stream_url"] = self.stream
        return out

    def to_signals(self) -> Dict[str, Any]:
        sig: Dict[str, Any] = {"title": self.title, "medium": "podcast"}
        if self.duration is not None:
            sig["duration"] = self.duration
        return sig


# ---------------------------------------------------------------------------
# Track
# ---------------------------------------------------------------------------

@dataclass
class Track:
    """A music track.

    .. note::
        iHeartRadio does not expose stream URLs for individual tracks.
        Use :meth:`search_stations` or :meth:`search_artist` for playable
        content.
    """

    id: int
    title: str
    artist: str = ""
    album: str = ""
    image: str = ""
    artist_id: Optional[int] = None
    album_id: Optional[int] = None

    def to_external_ids(self) -> Dict[str, str]:
        out: Dict[str, str] = {"iheart_track_id": str(self.id)}
        if self.artist_id is not None:
            out["iheart_artist_id"] = str(self.artist_id)
        return out

    def to_signals(self) -> Dict[str, Any]:
        sig: Dict[str, Any] = {"title": self.title, "medium": "music"}
        if self.artist:
            sig["artist"] = self.artist
        if self.album:
            sig["album"] = self.album
        return sig


# ---------------------------------------------------------------------------
# Artist
# ---------------------------------------------------------------------------

@dataclass
class Artist:
    """A music artist or band."""

    id: int
    title: str
    image: str = ""
    albums: List[dict] = field(default_factory=list)
    tracks: List[dict] = field(default_factory=list)
    related_artists: List[dict] = field(default_factory=list)

    def to_external_ids(self) -> Dict[str, str]:
        return {"iheart_artist_id": str(self.id)}

    def to_signals(self) -> Dict[str, Any]:
        return {"title": self.title, "medium": "music"}


# ---------------------------------------------------------------------------
# Playlist
# ---------------------------------------------------------------------------

@dataclass
class Playlist:
    """A curated playlist."""

    id: int
    title: str
    description: str = ""
    image: str = ""
    url: str = ""

    def to_external_ids(self) -> Dict[str, str]:
        return {"iheart_playlist_id": str(self.id)}

    def to_signals(self) -> Dict[str, Any]:
        return {"title": self.title, "medium": "music"}


# ---------------------------------------------------------------------------
# SearchResults — unified multi-type search
# ---------------------------------------------------------------------------

@dataclass
class SearchResults:
    """Results from a single unified search call across all entity types."""

    query: str
    stations: List[Station] = field(default_factory=list)
    podcasts: List[Podcast] = field(default_factory=list)
    artists: List[Artist] = field(default_factory=list)
    tracks: List[Track] = field(default_factory=list)
    playlists: List[Playlist] = field(default_factory=list)

    def __bool__(self) -> bool:
        return any([self.stations, self.podcasts, self.artists,
                    self.tracks, self.playlists])
