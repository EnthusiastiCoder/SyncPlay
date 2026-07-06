"""Tests for time utility functions."""

import pytest

from music_player.utils.time_utils import ms_to_display, ms_to_timestamp, timestamp_to_ms


class TestMsToDisplay:
    def test_zero(self):
        assert ms_to_display(0) == "0:00"

    def test_seconds_only(self):
        assert ms_to_display(5000) == "0:05"

    def test_minutes_and_seconds(self):
        assert ms_to_display(125000) == "2:05"

    def test_hours(self):
        assert ms_to_display(3661000) == "1:01:01"

    def test_negative_clamps_to_zero(self):
        assert ms_to_display(-500) == "0:00"

    def test_large_value(self):
        assert ms_to_display(7200000) == "2:00:00"


class TestMsToTimestamp:
    def test_zero(self):
        assert ms_to_timestamp(0) == "00:00:00.000"

    def test_with_milliseconds(self):
        assert ms_to_timestamp(1234) == "00:00:01.234"

    def test_full_timestamp(self):
        assert ms_to_timestamp(3723456) == "01:02:03.456"

    def test_negative_clamps_to_zero(self):
        assert ms_to_timestamp(-100) == "00:00:00.000"


class TestTimestampToMs:
    def test_hhmmss_ms(self):
        assert timestamp_to_ms("01:02:03.456") == 3723456

    def test_mmss_ms(self):
        assert timestamp_to_ms("02:03.456") == 123456

    def test_no_milliseconds(self):
        assert timestamp_to_ms("01:30:00") == 5400000

    def test_mmss_no_ms(self):
        assert timestamp_to_ms("02:30") == 150000

    def test_round_trip(self):
        for ms in [0, 500, 12345, 3723456, 7200000]:
            assert timestamp_to_ms(ms_to_timestamp(ms)) == ms

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            timestamp_to_ms("invalid")
