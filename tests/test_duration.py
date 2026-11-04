from __future__ import annotations

import unittest

from notionsyncyoutube.duration import (
    LENGTH_16_30M,
    LENGTH_31_60M,
    LENGTH_61_120M,
    LENGTH_121_180M,
    LENGTH_180M_PLUS,
    LENGTH_LE_15M,
    DurationMapper,
)


class DurationMapperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mapper = DurationMapper()

    def test_parses_youtube_iso8601_durations(self) -> None:
        self.assertEqual(3723, self.mapper.to_seconds("PT1H2M3S"))
        self.assertEqual(120, self.mapper.to_seconds("PT2M"))
        self.assertEqual(0, self.mapper.to_seconds("invalid"))

    def test_maps_duration_boundaries_to_notion_length_options(self) -> None:
        cases = (
            (15 * 60, LENGTH_LE_15M),
            (15 * 60 + 1, LENGTH_16_30M),
            (30 * 60, LENGTH_16_30M),
            (30 * 60 + 1, LENGTH_31_60M),
            (60 * 60, LENGTH_31_60M),
            (60 * 60 + 1, LENGTH_61_120M),
            (120 * 60, LENGTH_61_120M),
            (120 * 60 + 1, LENGTH_121_180M),
            (180 * 60, LENGTH_121_180M),
            (180 * 60 + 1, LENGTH_180M_PLUS),
            (10 * 60 * 60, LENGTH_180M_PLUS),
        )

        for seconds, expected in cases:
            with self.subTest(seconds=seconds):
                self.assertEqual(expected, self.mapper.map_seconds_to_length(seconds))

    def test_maps_long_youtube_durations_to_length_options(self) -> None:
        cases = (
            ("PT1H10M", LENGTH_61_120M),
            ("PT2H", LENGTH_61_120M),
            ("PT2H30M", LENGTH_121_180M),
            ("PT3H", LENGTH_121_180M),
            ("PT3H1S", LENGTH_180M_PLUS),
        )

        for duration, expected in cases:
            with self.subTest(duration=duration):
                self.assertEqual(expected, self.mapper.map_to_length(duration))

    def test_missing_or_zero_duration_has_no_length_option(self) -> None:
        self.assertIsNone(self.mapper.map_to_length(None))
        self.assertIsNone(self.mapper.map_seconds_to_length(0))


if __name__ == "__main__":
    unittest.main()
