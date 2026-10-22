"""Tests for the shared UTC normalization helper (BUG-4).

The PAES routes used to normalize datetimes with
``dt.replace(tzinfo=timezone.utc if dt.tzinfo is None else None)``.
That expression REPLACES the tzinfo of an aware datetime with ``None``,
producing a naive value that cannot be subtracted from an aware ``now``
(``TypeError: can't subtract offset-naive and offset-aware datetimes``).

These tests pin the behaviour of the single shared helper that replaced it.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).parent.parent


def test_to_utc_aware_treats_naive_datetimes_as_utc():
    """A naive datetime is interpreted as UTC (SQLite stores naive UTC)."""
    from core.timeutils import to_utc_aware

    converted = to_utc_aware(datetime(2026, 1, 5, 12, 0, 0))

    assert converted.tzinfo is not None
    assert converted.utcoffset() == timedelta(0)
    assert converted == datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)


def test_to_utc_aware_converts_aware_datetimes_to_utc():
    """An aware datetime keeps its instant and is expressed in UTC."""
    from core.timeutils import to_utc_aware

    santiago_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=timezone(timedelta(hours=-3)))

    converted = to_utc_aware(santiago_time)

    assert converted.tzinfo == timezone.utc
    assert converted == datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)


def test_elapsed_days_is_identical_for_naive_and_aware_inputs():
    """Naive and aware inputs describing the same instant yield the same elapsed days."""
    from core.timeutils import elapsed_days

    now_utc = datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)
    naive_last = datetime(2026, 1, 4, 12, 0, 0)
    aware_last = datetime(2026, 1, 4, 12, 0, 0, tzinfo=timezone.utc)

    assert elapsed_days(naive_last, now_utc) == pytest.approx(1.0)
    assert elapsed_days(aware_last, now_utc) == pytest.approx(1.0)


def test_elapsed_days_never_returns_negative_values():
    """A future timestamp is clamped to 0 elapsed days instead of going negative."""
    from core.timeutils import elapsed_days

    now_utc = datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)

    assert elapsed_days(datetime(2026, 1, 6, 12, 0, 0, tzinfo=timezone.utc), now_utc) == 0.0


def test_backend_code_no_longer_uses_replace_tzinfo_gymnastics():
    """No module under api/, services/, core/ or models/ may strip/replace tzinfo.

    Every datetime comparison in the backend must go through the shared
    ``core.timeutils`` helpers instead.
    """
    offenders = []
    for folder in ("api", "services", "core", "models"):
        for path in (BACKEND_ROOT / folder).rglob("*.py"):
            if path.name == "timeutils.py" and path.parent.name == "core":
                continue  # the single sanctioned normalization helper
            content = path.read_text(encoding="utf-8", errors="ignore")
            if "replace(tzinfo=" in content:
                offenders.append(
                    f"{path.relative_to(BACKEND_ROOT)}: contains 'replace(tzinfo='"
                )

    assert offenders == [], (
        "Datetime normalization must use core.timeutils.to_utc_aware instead of "
        "replace(tzinfo=...):\n" + "\n".join(offenders)
    )


def test_study_timezone_applies_the_chilean_offsets():
    """The study timezone uses UTC-3 in summer and UTC-4 in winter."""
    from core.timeutils import SANTIAGO_TZ

    summer = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc).astimezone(SANTIAGO_TZ)
    winter = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc).astimezone(SANTIAGO_TZ)

    assert summer.utcoffset() == timedelta(hours=-3)
    assert winter.utcoffset() == timedelta(hours=-4)


def test_study_timezone_has_one_short_and_one_long_day_per_year():
    """Every local year has exactly one 23-hour and one 25-hour day."""
    from core.timeutils import SANTIAGO_TZ

    for year in (2025, 2026):
        noon = datetime(year, 1, 1, 12, 0, tzinfo=SANTIAGO_TZ)
        lengths = []
        while noon.year == year:
            next_noon = (noon + timedelta(days=1)).astimezone(timezone.utc)
            lengths.append(next_noon - noon.astimezone(timezone.utc))
            noon = noon + timedelta(days=1)

        assert lengths.count(timedelta(hours=23)) == 1, f"{year} has no 23-hour day"
        assert lengths.count(timedelta(hours=25)) == 1, f"{year} has no 25-hour day"
        assert set(lengths) <= {
            timedelta(hours=23),
            timedelta(hours=24),
            timedelta(hours=25),
        }, f"{year} has an unexpected local day length"
