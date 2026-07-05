from __future__ import annotations

from datetime import datetime, timezone

from notionsyncyoutube.config import Config
from notionsyncyoutube.duration import DurationMapper
from notionsyncyoutube.http import HttpClient
from notionsyncyoutube.models import SyncSummary, Video
from notionsyncyoutube.notion import NotionClient
from notionsyncyoutube.youtube import YouTubeClient


class YouTubeInboxSync:
    def __init__(
        self,
        config: Config,
        youtube_client: YouTubeClient,
        notion_client: NotionClient,
        duration_mapper: DurationMapper,
    ) -> None:
        self.config = config
        self.youtube_client = youtube_client
        self.notion_client = notion_client
        self.duration_mapper = duration_mapper

    def run(self) -> SyncSummary:
        print("Fetching YouTube playlist items...")
        videos = self.youtube_client.fetch_playlist_videos(self.config.youtube_playlist_id)
        print(f"Fetched {len(videos)} YouTube videos.")

        videos = self._attach_lengths(videos)

        created = 0
        updated = 0
        skipped = 0
        errors = 0

        for video in videos:
            try:
                existing = self.notion_client.find_page_by_video_id(video.video_id)

                if existing:
                    page_id = existing.get("id")

                    if not isinstance(page_id, str):
                        skipped += 1
                        print(f"SKIP   {video.title} [{video.video_id}] missing Notion page id")
                        continue

                    self.notion_client.update_video_page(
                        page_id,
                        video,
                        category=self.config.default_category,
                    )
                    updated += 1
                    print(f"UPDATE {video.title} [{video.video_id}]")
                    continue

                self.notion_client.create_video_page(
                    video,
                    category=self.config.default_category,
                    status=self.config.default_status,
                )
                created += 1
                print(f"CREATE {video.title} [{video.video_id}]")

            except Exception as exc:
                errors += 1
                print(f"ERROR  {video.title} [{video.video_id}]: {exc}")

        return SyncSummary(
            fetched=len(videos),
            created=created,
            updated_existing=updated,
            skipped_existing=skipped,
            errors=errors,
            synced_at=datetime.now(timezone.utc).isoformat(),
        )

    def _attach_lengths(self, videos: list[Video]) -> list[Video]:
        video_ids = [video.video_id for video in videos]
        durations = self.youtube_client.fetch_video_durations(video_ids)

        return [
            video.with_length(self.duration_mapper.map_to_length(durations.get(video.video_id))) for video in videos
        ]


def build_sync(config: Config) -> YouTubeInboxSync:
    http_client = HttpClient()
    youtube_client = YouTubeClient(config.youtube_api_key, http_client)
    notion_client = NotionClient(
        token=config.notion_token,
        database_id=config.notion_database_id,
        notion_version=config.notion_version,
        http_client=http_client,
    )

    return YouTubeInboxSync(
        config=config,
        youtube_client=youtube_client,
        notion_client=notion_client,
        duration_mapper=DurationMapper(),
    )
