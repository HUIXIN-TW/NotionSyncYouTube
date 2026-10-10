"""Tests for the one-time Format backfill, without live Notion writes."""

import unittest

from notionsyncyoutube.backfill import backfill, collect_candidates


def page(page_id, category, format_name=None):
    return {
        "id": page_id,
        "properties": {
            "Category": {"select": {"name": category}},
            "Format": {"select": {"name": format_name} if format_name else None},
        },
    }


class FakeHttp:
    def __init__(self):
        self.requests = []

    def request_json(self, method, url, *, headers, json_body=None):
        self.requests.append((method, url, json_body))
        if method == "PATCH":
            return {"id": url.rsplit("/", 1)[-1]}
        if "start_cursor" in json_body:
            return {
                "results": [
                    page("v3", "Youtube"),
                    page("v4", "Kindle"),
                    page("v5", "Podcast"),
                    page("v6", "Audible"),
                ],
                "has_more": False,
                "next_cursor": None,
            }
        return {
            "results": [
                page("v1", "Youtube"),
                page("v2", "Youtube", "Video"),
                page("unknown", "Book"),
            ],
            "has_more": True,
            "next_cursor": "cursor2",
        }


class FormatBackfillTests(unittest.TestCase):
    def test_snapshot_skips_already_classified_and_unsupported_types(self):
        http = FakeHttp()
        rows = collect_candidates(http, token="token", data_source_id="ds")
        self.assertEqual([(r.page_id, r.format) for r in rows], [
            ("v1", "Video"), ("v3", "Video"), ("v4", "Ebook"),
            ("v5", "Audio"), ("v6", "Audio"),
        ])
        self.assertEqual(len(http.requests), 2)
        self.assertEqual(http.requests[1][2]["start_cursor"], "cursor2")

    def test_dry_run_is_read_only_and_apply_changes_only_format(self):
        http = FakeHttp()
        preview = backfill(http, token="token", data_source_id="ds")
        self.assertEqual(preview, {"candidates": 5, "updated": 0, "failed": 0})
        self.assertTrue(all(req[0] == "POST" for req in http.requests))

        http = FakeHttp()
        result = backfill(http, token="token", data_source_id="ds", apply=True)
        self.assertEqual(result, {"candidates": 5, "updated": 5, "failed": 0})
        updates = [req for req in http.requests if req[0] == "PATCH"]
        self.assertEqual(len(updates), 5)
        self.assertEqual(
            updates[0][2]["properties"],
            {"Format": {"select": {"name": "Video"}}},
        )
        self.assertTrue(all("Category" not in req[2]["properties"] for req in updates))


if __name__ == "__main__":
    unittest.main()
