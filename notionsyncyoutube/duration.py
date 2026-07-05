from __future__ import annotations

import re


LENGTH_LE_15M = "<= 15m"
LENGTH_16_30M = "16-30m"
LENGTH_31_60M = "31-60m"
LENGTH_60M_PLUS = "60m+"


class DurationMapper:
    _youtube_duration_pattern = re.compile(
        r"^PT" r"(?:(?P<hours>\d+)H)?" r"(?:(?P<minutes>\d+)M)?" r"(?:(?P<seconds>\d+)S)?$"
    )

    def map_to_length(self, duration: str | None) -> str | None:
        if not duration:
            return None

        return self.map_seconds_to_length(self.to_seconds(duration))

    def map_seconds_to_length(self, seconds: int | None) -> str | None:
        if seconds is None or seconds <= 0:
            return None

        minutes = seconds / 60

        if minutes <= 15:
            return LENGTH_LE_15M

        if minutes <= 30:
            return LENGTH_16_30M

        if minutes <= 60:
            return LENGTH_31_60M

        return LENGTH_60M_PLUS

    def to_seconds(self, duration: str) -> int:
        match = self._youtube_duration_pattern.match(duration)

        if not match:
            return 0

        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        seconds = int(match.group("seconds") or 0)

        return hours * 3600 + minutes * 60 + seconds
