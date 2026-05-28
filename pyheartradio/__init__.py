from typing import Iterator, Optional
import requests


class IHeartRadio:
    search_url = "https://us.api.iheart.com/api/v3/search/all"
    podcast_episodes_url = "https://us.api.iheart.com/api/v3/podcast/podcasts/{podcast_id}/episodes"
    podcast_stream_url = "https://us.api.iheart.com/api/v3/podcast/episodes/{episode_id}"
    station_stream_url = "https://us.api.iheart.com/api/v2/content/liveStations/{stream_id}"
    artist_profile_url = "https://us.api.iheart.com/api/v3/artists/profiles/{artist_id}"

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout
        self.session = requests.Session()

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

    def search_stations(self, search_term: str) -> Iterator[dict]:
        data = self._get(self.search_url, self._search_payload(search_term, station="true"))
        for station in data.get("results", {}).get("stations", []):
            station_id = station["id"]
            res = self._get(self.station_stream_url.format(stream_id=station_id))
            hit = res.get("hits", [{}])[0]
            streams = hit.get("streams", {})
            stream_url = next(iter(streams.values()), None)
            if stream_url:
                yield {
                    "title": station["name"],
                    "description": hit.get("description", ""),
                    "stream": stream_url,
                    "image": hit.get("logo", ""),
                    "id": station_id,
                }

    def search_podcast(self, search_term: str) -> Iterator[dict]:
        data = self._get(self.search_url, self._search_payload(search_term, podcast="true"))
        for podcast in data.get("results", {}).get("podcasts", []):
            yield {
                "title": podcast.get("title", ""),
                "image": podcast.get("image", ""),
                "description": podcast.get("description", ""),
                "id": podcast["id"],
            }

    def get_podcast_episodes(self, podcast_id: int) -> Iterator[dict]:
        res = self._get(self.podcast_episodes_url.format(podcast_id=podcast_id))
        for episode in res.get("data", []):
            episode_id = episode["id"]
            stream_res = self._get(self.podcast_stream_url.format(episode_id=episode_id))
            yield {
                "title": episode.get("title", ""),
                "duration": episode.get("duration"),
                "image": episode.get("imageUrl", ""),
                "id": episode_id,
                "description": episode.get("description", ""),
                "stream": stream_res.get("episode", {}).get("mediaUrl", ""),
            }

    def search_track(self, search_term: str) -> Iterator[dict]:
        """Search for tracks. Stream URLs are not available via this API."""
        data = self._get(self.search_url, self._search_payload(search_term, track="true"))
        for track in data.get("results", {}).get("tracks", []):
            yield {
                "title": track.get("title", ""),
                "album": track.get("albumName", ""),
                "artist": track.get("artistName", ""),
                "image": track.get("image", ""),
                "id": track["id"],
                "artist_id": track.get("artistId"),
                "album_id": track.get("albumId"),
            }

    def search_artist(self, search_term: str) -> Iterator[dict]:
        data = self._get(self.search_url, self._search_payload(search_term, artist="true"))
        for artist in data.get("results", {}).get("artists", []):
            artist_id = artist["id"]
            profile = self._get(self.artist_profile_url.format(artist_id=artist_id))
            yield {
                "title": artist["name"],
                "albums": profile.get("albums", []),
                "tracks": profile.get("tracks", []),
                "related_artist": profile.get("relatedTo", []),
                "image": artist.get("image", ""),
                "id": artist_id,
            }

    def search_playlist(self, search_term: str) -> Iterator[dict]:
        data = self._get(self.search_url, self._search_payload(search_term, playlist="true"))
        for playlist in data.get("results", {}).get("playlists", []):
            urls = playlist.get("urls", {})
            yield {
                "title": playlist.get("name", ""),
                "url": urls.get("web", ""),
                "description": playlist.get("description", ""),
                "image": urls.get("image", ""),
                "id": playlist["id"],
            }
