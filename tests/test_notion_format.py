"""Regression tests for the Notion Format-only video metadata contract."""

import unittest

from notionsyncyoutube.models import Video
from notionsyncyoutube.notion import NotionClient


class FakeHttpClient:
    def __init__(self):
        self.calls = []

    def request_json(self, method, url, *, headers, json_body=None):
        self.calls.append((method, url, json_body))
        return {"id": "page-id"}


class NotionVideoFormatTests(unittest.TestCase):
    def setUp(self):
        self.http = FakeHttpClient()
        self.client = NotionClient(
            token="test-token",
            database_id="database-id",
            data_source_id="data-source-id",
            notion_version="2025-09-03",
            http_client=self.http,
        )
        self.video = Video(
            video_id="abc123",
            title="Test video",
            url="https://www.youtube.com/watch?v=abc123",
            length="16-30m",
        )

    def test_create_writes_format_video_and_backlog_but_not_category(self):
        self.client.create_video_page(self.video, status="Backlog")
        method, url, body = self.http.calls[-1]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://api.notion.com/v1/pages")
        properties = body["properties"]
        self.assertEqual(properties["Format"], {"select": {"name": "Video"}})
        self.assertEqual(properties["Status"], {"status": {"name": "Backlog"}})
        self.assertEqual(properties["Length"], {"select": {"name": "16-30m"}})
        self.assertNotIn("Category", properties)

    def test_update_writes_format_but_preserves_status_and_category(self):
        self.client.update_video_page("existing-page", self.video)
        method, url, body = self.http.calls[-1]
        self.assertEqual(method, "PATCH")
        self.assertTrue(url.endswith("/existing-page"))
        properties = body["properties"]
        self.assertEqual(properties["Format"], {"select": {"name": "Video"}})
        self.assertEqual(properties["Video ID"]["rich_text"][0]["text"]["content"], "abc123")
        self.assertNotIn("Status", properties)
        self.assertNotIn("Category", properties)

    def test_length_not_cleared_when_video_duration_unknown(self):
        unknown = Video(video_id="abc123", title="Test", url=self.video.url)
        self.client.update_video_page("existing-page", unknown)
        properties = self.http.calls[-1][2]["properties"]
        self.assertNotIn("Length", properties)
        self.assertEqual(properties["Format"]["select"]["name"], "Video")


if __name__ == "__main__":
    unittest.main()
