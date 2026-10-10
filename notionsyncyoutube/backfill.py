"""One-time migration of the legacy Category values to canonical Format.

Existing non-empty Format values are never overwritten. This is a maintenance
script, not a backward-compatibility path in the YouTube synchronization runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from notionsyncyoutube.http import HttpClient


FORMAT_BY_CATEGORY = {
    "Youtube": "Video",
    "Podcast": "Audio",
    "Audible": "Audio",
    "Kindle": "Ebook",
}
NOTION_VERSION = "2025-09-03"


@dataclass(frozen=True)
class Candidate:
    page_id: str
    category: str
    format: str


def collect_candidates(http: HttpClient, *, token: str, data_source_id: str) -> list[Candidate]:
    """Snapshot all eligible IDs before any writes so pagination remains stable."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    endpoint = f"https://api.notion.com/v1/data_sources/{data_source_id}/query"
    cursor: str | None = None
    candidates: list[Candidate] = []

    while True:
        payload: dict[str, Any] = {
            "filter": {"property": "Format", "multi_select": {"is_empty": True}},
            "page_size": 100,
        }
        if cursor:
            payload["start_cursor"] = cursor
        response = http.request_json("POST", endpoint, headers=headers, json_body=payload)

        for page in response.get("results", []):
            properties = page.get("properties", {})
            category = (properties.get("Category", {}).get("select") or {}).get("name")
            current_formats = properties.get("Format", {}).get("multi_select") or []
            target_format = FORMAT_BY_CATEGORY.get(category)
            page_id = page.get("id")
            if page_id and target_format and not current_formats:
                candidates.append(Candidate(page_id, category, target_format))

        if not response.get("has_more", False):
            break
        cursor = response.get("next_cursor")
        if not cursor:
            raise RuntimeError("Notion reports additional pages but no next_cursor")

    return candidates


def backfill(
    http: HttpClient,
    *,
    token: str,
    data_source_id: str,
    apply: bool = False,
) -> dict[str, int]:
    """Preview by default. Apply only when requested; preserve every other field."""
    candidates = collect_candidates(http, token=token, data_source_id=data_source_id)
    result = {"candidates": len(candidates), "updated": 0, "failed": 0}
    for candidate in candidates:
        print(f"{'APPLY' if apply else 'DRY RUN'} {candidate.page_id} "
              f"{candidate.category} -> {candidate.format}")
        if not apply:
            continue
        try:
            http.request_json(
                "PATCH",
                f"https://api.notion.com/v1/pages/{candidate.page_id}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Notion-Version": NOTION_VERSION,
                    "Content-Type": "application/json",
                },
                json_body={
                    "properties": {"Format": {"multi_select": [{"name": candidate.format}]}},
                },
            )
            result["updated"] += 1
        except Exception as exc:
            print(f"ERROR {candidate.page_id}: {exc}")
            result["failed"] += 1
    return result
