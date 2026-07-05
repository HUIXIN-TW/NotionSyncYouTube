from __future__ import annotations

from typing import Any

from notionsyncyoutube.http import HttpClient
from notionsyncyoutube.models import Video


NOTION_PAGES_URL = "https://api.notion.com/v1/pages"


class NotionClient:
    def __init__(
        self,
        token: str,
        database_id: str,
        notion_version: str,
        http_client: HttpClient,
    ) -> None:
        self.token = token
        self.database_id = database_id
        self.notion_version = notion_version
        self.http_client = http_client

    def verify_database_access(self) -> None:
        self.http_client.request_json(
            "GET",
            f"https://api.notion.com/v1/databases/{self.database_id}",
            headers=self._headers(),
        )

    def find_page_by_video_id(self, video_id: str) -> dict[str, Any] | None:
        url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        payload = {
            "filter": {
                "property": "Video ID",
                "rich_text": {
                    "equals": video_id,
                },
            },
            "page_size": 1,
        }

        data = self.http_client.request_json(
            "POST",
            url,
            headers=self._headers(),
            json_body=payload,
        )

        results = data.get("results", [])

        if not isinstance(results, list) or not results:
            return None

        first_result = results[0]
        return first_result if isinstance(first_result, dict) else None

    def create_video_page(
        self,
        video: Video,
        category: str,
        status: str,
    ) -> dict[str, Any]:
        payload = {
            "parent": {
                "database_id": self.database_id,
            },
            "properties": self._build_video_properties(video, category, status),
        }

        return self.http_client.request_json(
            "POST",
            NOTION_PAGES_URL,
            headers=self._headers(),
            json_body=payload,
        )

    def update_video_page(
        self,
        page_id: str,
        video: Video,
        category: str,
    ) -> dict[str, Any]:
        payload = {
            "properties": self._build_video_properties(video, category, None),
        }

        return self.http_client.request_json(
            "PATCH",
            f"{NOTION_PAGES_URL}/{page_id}",
            headers=self._headers(),
            json_body=payload,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": self.notion_version,
            "Content-Type": "application/json",
        }

    def _build_video_properties(
        self,
        video: Video,
        category: str,
        status: str | None,
    ) -> dict[str, Any]:
        properties: dict[str, Any] = {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": video.title[:2000],
                        },
                    },
                ],
            },
            "Category": {
                "select": {
                    "name": category,
                },
            },
            "URL": {
                "url": video.url,
            },
            "Video ID": {
                "rich_text": [
                    {
                        "text": {
                            "content": video.video_id,
                        },
                    },
                ],
            },
        }

        if status:
            properties["Status"] = {
                "status": {
                    "name": status,
                },
            }

        if video.length:
            properties["Length"] = {
                "select": {
                    "name": video.length,
                },
            }

        return properties
