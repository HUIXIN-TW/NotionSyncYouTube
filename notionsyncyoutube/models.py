from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Video:
    video_id: str
    title: str
    url: str
    length: str | None = None

    def with_length(self, length: str | None) -> "Video":
        return Video(
            video_id=self.video_id,
            title=self.title,
            url=self.url,
            length=length,
        )


@dataclass(frozen=True)
class SyncSummary:
    fetched: int
    created: int
    skipped_existing: int
    errors: int
    synced_at: str

    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=2, ensure_ascii=False)
