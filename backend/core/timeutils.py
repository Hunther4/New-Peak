"""Shared datetime normalization helpers.

SQLite returns naive datetimes while Postgres returns timezone-aware ones.
Every comparison between a stored timestamp and "now" must go through these
helpers: mixing naive and aware values raises
``TypeError: can't subtract offset-naive and offset-aware datetimes``, and
stripping the tzinfo (``dt.replace(tzinfo=None)``) silently changes the
instant being compared.

This module also owns the study timezone (``America/Santiago``). Windows
ships no IANA time zone database and ``zoneinfo`` cannot read
``tzres.dll``, so ``ZoneInfo("America/Santiago")`` raises
``ZoneInfoNotFoundError`` there. Rather than adding a dependency, the module
falls back to an equivalent implementation of the Chilean rule.
"""
from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

__all__ = [
    "to_utc_aware",
    "elapsed_days",
    "SANTIAGO_TZ",
    "STUDY_TIMEZONE_KEY",
]

#: IANA key of the timezone used to resolve "today" for the PAES students.
STUDY_TIMEZONE_KEY = "America/Santiago"


def to_utc_aware(value: datetime) -> datetime:
    """Return ``value`` as a timezone-aware datetime expressed in UTC.

    Naive datetimes are interpreted as UTC (that is what SQLite stores).
    Aware datetimes keep their instant and are converted to UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def elapsed_days(since: datetime, now: datetime) -> float:
    """Days elapsed between ``since`` and ``now``. Never negative."""
    delta = to_utc_aware(now) - to_utc_aware(since)
    return max(0.0, delta.total_seconds() / 86400.0)


class _SantiagoFallback(tzinfo):
    """``America/Santiago`` for platforms without an IANA time zone database.

    Chile's rule is small enough to encode exactly:

    * daylight saving time (UTC-3) starts on the first Saturday of September
      at 24:00 local standard time;
    * it ends on the first Saturday of April at 24:00 local daylight time.

    Outside the daylight saving period the offset is UTC-4.
    """

    STANDARD = timedelta(hours=-4)
    DAYLIGHT = timedelta(hours=-3)

    @staticmethod
    def _first_saturday(year: int, month: int) -> datetime:
        """Date of the first Saturday of ``month`` in ``year``."""
        first = datetime(year, month, 1)
        return first + timedelta(days=(5 - first.weekday()) % 7)

    def _transition_utc(self, year: int, month: int, utc_offset_hours: int) -> datetime:
        """UTC instant of the transition that happens at 24:00 on the first Saturday."""
        saturday = self._first_saturday(year, month)
        return saturday + timedelta(days=1, hours=utc_offset_hours)

    def _daylight_window(self, year: int) -> tuple[datetime, datetime]:
        """UTC bounds of the daylight saving period that ends in ``year``."""
        start = self._transition_utc(year - 1, 9, 4)  # 00:00 local standard time
        end = self._transition_utc(year, 4, 3)  # 00:00 local daylight time
        return start, end

    def _offset_at(self, moment_utc: datetime) -> timedelta:
        """UTC offset in effect at the given naive UTC instant."""
        naive = moment_utc.replace(tzinfo=None)
        for year in (naive.year - 1, naive.year, naive.year + 1):
            start, end = self._daylight_window(year)
            if start <= naive < end:
                return self.DAYLIGHT
        return self.STANDARD

    def utcoffset(self, dt: datetime | None) -> timedelta:
        if dt is None:
            return self.STANDARD
        naive = dt.replace(tzinfo=None)
        fold = getattr(dt, "fold", 0)
        order = (self.DAYLIGHT, self.STANDARD) if fold == 0 else (self.STANDARD, self.DAYLIGHT)
        for offset in order:
            if self._offset_at(naive - offset) == offset:
                return offset
        return self.STANDARD

    def dst(self, dt: datetime | None) -> timedelta:
        offset = self.utcoffset(dt)
        return offset - self.STANDARD if offset != self.STANDARD else timedelta(0)

    def tzname(self, dt: datetime | None) -> str:
        return "CLST" if self.utcoffset(dt) == self.DAYLIGHT else "CLT"

    def fromutc(self, dt: datetime) -> datetime:
        naive = dt.replace(tzinfo=None)
        offset = self._offset_at(naive)
        local = (naive + offset).replace(tzinfo=self)
        if local.utcoffset() != offset:
            # PEP 495: the local time is ambiguous, this is its second pass.
            local = local.replace(fold=1)
        return local


def _resolve_study_timezone() -> tzinfo:
    """``ZoneInfo`` for the study timezone, with a dependency-free fallback."""
    try:
        return ZoneInfo(STUDY_TIMEZONE_KEY)
    except (ZoneInfoNotFoundError, KeyError, OSError):
        return _SantiagoFallback()


#: Timezone used to resolve "today" for the PAES students (Chile).
SANTIAGO_TZ: tzinfo = _resolve_study_timezone()
