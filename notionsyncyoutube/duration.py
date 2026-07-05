from __future__ import annotations

import re


class DurationMapper:
    _youtube_duration_pattern = re.compile(
        r"^PT"
        r"(?:(?P<hours>\d+)H)?"
        r"(?:(?P<minutes>\d+)M)?"
        r"(?:(?P<seconds>\d+)S)?$"
    )

    def map_to_length(self, duration: str | None) -> str | None:
        if not duration:
            return None

        seconds = self.to_seconds(duration)

        if seconds <= 0:
            return None

        minutes = seconds / 60

        if minutes <= 15:
            return "<= 15m"

        if minutes <= 60:
            return "30–60m"

        return "60m+"

    def to_seconds(self, duration: str) -> int:
        match = self._youtube_duration_pattern.match(duration)

        if not match:
            return 0

        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        seconds = int(match.group("seconds") or 0)

        return hours * 3600 + minutes * 60 + seconds
