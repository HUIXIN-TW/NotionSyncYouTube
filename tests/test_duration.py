from __future__ import annotations

import unittest

from notionsyncyoutube.duration import (
    LENGTH_16_30M,
    LENGTH_31_60M,
    LENGTH_60M_PLUS,
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
            (60 * 60 + 1, LENGTH_60M_PLUS),
        )

        for seconds, expected in cases:
            with self.subTest(seconds=seconds):
                self.assertEqual(expected, self.mapper.map_seconds_to_length(seconds))

    def test_missing_or_zero_duration_has_no_length_option(self) -> None:
        self.assertIsNone(self.mapper.map_to_length(None))
        self.assertIsNone(self.mapper.map_seconds_to_length(0))


if __name__ == "__main__":
    unittest.main()
