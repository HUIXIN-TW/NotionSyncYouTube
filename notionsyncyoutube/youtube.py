from __future__ import annotations

from typing import Any

from notionsyncyoutube.http import HttpClient
from notionsyncyoutube.models import Video
from notionsyncyoutube.utils import chunked


YOUTUBE_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


class YouTubeClient:
    def __init__(self, api_key: str, http_client: HttpClient) -> None:
        self.api_key = api_key
        self.http_client = http_client

    def fetch_playlist_videos(self, playlist_id: str) -> list[Video]:
        videos: list[Video] = []
        page_token: str | None = None

        while True:
            params = {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": 50,
                "key": self.api_key,
            }

            if page_token:
                params["pageToken"] = page_token

            data = self.http_client.request_json(
                "GET",
                YOUTUBE_PLAYLIST_ITEMS_URL,
                params=params,
            )

            videos.extend(self._parse_playlist_items(data.get("items", [])))

            page_token = data.get("nextPageToken")
            if not page_token:
                return videos

    def fetch_video_durations(self, video_ids: list[str]) -> dict[str, str]:
        durations: dict[str, str] = {}

        for batch in chunked(video_ids, 50):
            params = {
                "part": "contentDetails",
                "id": ",".join(batch),
                "key": self.api_key,
            }

            data = self.http_client.request_json(
                "GET",
                YOUTUBE_VIDEOS_URL,
                params=params,
            )

            for item in data.get("items", []):
                if not isinstance(item, dict):
                    continue

                video_id = item.get("id")
                duration = item.get("contentDetails", {}).get("duration")

                if isinstance(video_id, str) and isinstance(duration, str):
                    durations[video_id] = duration

        return durations

    def _parse_playlist_items(self, items: Any) -> list[Video]:
        if not isinstance(items, list):
            return []

        videos: list[Video] = []

        for item in items:
            if not isinstance(item, dict):
                continue

            snippet = item.get("snippet", {})
            content_details = item.get("contentDetails", {})

            if not isinstance(snippet, dict) or not isinstance(content_details, dict):
                continue

            video_id = content_details.get("videoId")
            title = snippet.get("title")

            if not isinstance(video_id, str) or not isinstance(title, str):
                continue

            if title in {"Deleted video", "Private video"}:
                continue

            videos.append(
                Video(
                    video_id=video_id,
                    title=title,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                )
            )

        return videos
