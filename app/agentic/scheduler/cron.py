"""
Cron Expression Parser

Parses and evaluates cron expressions for job scheduling.
Supports standard 5-field cron format: minute hour day month weekday

Examples:
- "0 9 * * 1-5"  → 9 AM every weekday
- "*/15 * * * *" → Every 15 minutes
- "0 0 1 * *"    → Midnight on the 1st of each month
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)


class CronParseError(Exception):
    """Error parsing cron expression."""
    pass


@dataclass
class CronField:
    """A single field in a cron expression."""
    values: Set[int]
    min_val: int
    max_val: int

    def matches(self, value: int) -> bool:
        """Check if a value matches this field."""
        return value in self.values


@dataclass
class CronExpression:
    """Parsed cron expression."""
    minute: CronField      # 0-59
    hour: CronField        # 0-23
    day_of_month: CronField  # 1-31
    month: CronField       # 1-12
    day_of_week: CronField  # 0-6 (0 = Sunday)

    original: str = ""

    def matches(self, dt: datetime) -> bool:
        """Check if a datetime matches this cron expression."""
        return (
            self.minute.matches(dt.minute) and
            self.hour.matches(dt.hour) and
            self.day_of_month.matches(dt.day) and
            self.month.matches(dt.month) and
            self.day_of_week.matches(dt.weekday())  # Python: 0=Monday
        )

    def next_run(self, after: Optional[datetime] = None) -> datetime:
        """Calculate the next run time after a given datetime."""
        if after is None:
            after = datetime.utcnow()

        # Start from the next minute
        current = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Search up to 4 years ahead (handles leap years)
        max_iterations = 60 * 24 * 366 * 4
        iterations = 0

        while iterations < max_iterations:
            if self.matches(current):
                return current

            # Advance by 1 minute
            current += timedelta(minutes=1)
            iterations += 1

        # Fallback: couldn't find a match
        raise CronParseError(f"Could not find next run time for: {self.original}")

    def next_runs(self, count: int, after: Optional[datetime] = None) -> List[datetime]:
        """Get the next N run times."""
        runs = []
        current = after

        for _ in range(count):
            next_run = self.next_run(current)
            runs.append(next_run)
            current = next_run

        return runs


class CronParser:
    """Parser for cron expressions."""

    # Named shortcuts
    SHORTCUTS = {
        "@yearly": "0 0 1 1 *",
        "@annually": "0 0 1 1 *",
        "@monthly": "0 0 1 * *",
        "@weekly": "0 0 * * 0",
        "@daily": "0 0 * * *",
        "@midnight": "0 0 * * *",
        "@hourly": "0 * * * *",
    }

    # Day name mappings
    DAYS = {
        "sun": 0, "sunday": 0,
        "mon": 1, "monday": 1,
        "tue": 2, "tuesday": 2,
        "wed": 3, "wednesday": 3,
        "thu": 4, "thursday": 4,
        "fri": 5, "friday": 5,
        "sat": 6, "saturday": 6,
    }

    # Month name mappings
    MONTHS = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }

    @classmethod
    def parse(cls, expression: str) -> CronExpression:
        """Parse a cron expression string."""
        expression = expression.strip().lower()

        # Check for shortcuts
        if expression in cls.SHORTCUTS:
            expression = cls.SHORTCUTS[expression]

        # Split into fields
        fields = expression.split()
        if len(fields) != 5:
            raise CronParseError(
                f"Invalid cron expression: expected 5 fields, got {len(fields)}"
            )

        try:
            minute = cls._parse_field(fields[0], 0, 59)
            hour = cls._parse_field(fields[1], 0, 23)
            day_of_month = cls._parse_field(fields[2], 1, 31)
            month = cls._parse_field(fields[3], 1, 12, cls.MONTHS)
            day_of_week = cls._parse_field(fields[4], 0, 6, cls.DAYS)

            return CronExpression(
                minute=minute,
                hour=hour,
                day_of_month=day_of_month,
                month=month,
                day_of_week=day_of_week,
                original=expression,
            )
        except Exception as e:
            raise CronParseError(f"Failed to parse cron expression '{expression}': {e}")

    @classmethod
    def _parse_field(
        cls,
        field: str,
        min_val: int,
        max_val: int,
        names: Optional[dict] = None
    ) -> CronField:
        """Parse a single cron field."""
        values: Set[int] = set()

        # Replace names with numbers
        if names:
            for name, num in names.items():
                field = field.replace(name, str(num))

        # Split by comma for multiple values/ranges
        for part in field.split(","):
            part = part.strip()

            # Handle step values (e.g., */5, 1-10/2)
            step = 1
            if "/" in part:
                part, step_str = part.split("/", 1)
                step = int(step_str)
                if step <= 0:
                    raise CronParseError(f"Invalid step value: {step}")

            # Handle wildcard
            if part == "*":
                values.update(range(min_val, max_val + 1, step))

            # Handle range (e.g., 1-5)
            elif "-" in part:
                start_str, end_str = part.split("-", 1)
                start = int(start_str)
                end = int(end_str)

                if start < min_val or end > max_val or start > end:
                    raise CronParseError(f"Invalid range: {part}")

                values.update(range(start, end + 1, step))

            # Handle single value
            else:
                val = int(part)
                if val < min_val or val > max_val:
                    raise CronParseError(f"Value out of range: {val}")
                values.add(val)

        if not values:
            raise CronParseError(f"No values parsed from field: {field}")

        return CronField(values=values, min_val=min_val, max_val=max_val)

    @classmethod
    def validate(cls, expression: str) -> Tuple[bool, Optional[str]]:
        """Validate a cron expression without fully parsing it."""
        try:
            cls.parse(expression)
            return True, None
        except CronParseError as e:
            return False, str(e)

    @classmethod
    def describe(cls, expression: str) -> str:
        """Generate a human-readable description of a cron expression."""
        try:
            cron = cls.parse(expression)
        except CronParseError:
            return f"Invalid expression: {expression}"

        parts = []

        # Minute
        if cron.minute.values == set(range(0, 60)):
            parts.append("every minute")
        elif len(cron.minute.values) == 1:
            val = list(cron.minute.values)[0]
            parts.append(f"at minute {val}")
        else:
            parts.append(f"at minutes {sorted(cron.minute.values)}")

        # Hour
        if cron.hour.values == set(range(0, 24)):
            parts.append("of every hour")
        elif len(cron.hour.values) == 1:
            val = list(cron.hour.values)[0]
            parts.append(f"at {val:02d}:00")
        else:
            parts.append(f"at hours {sorted(cron.hour.values)}")

        # Day of month
        if cron.day_of_month.values != set(range(1, 32)):
            if len(cron.day_of_month.values) == 1:
                val = list(cron.day_of_month.values)[0]
                parts.append(f"on day {val}")
            else:
                parts.append(f"on days {sorted(cron.day_of_month.values)}")

        # Month
        if cron.month.values != set(range(1, 13)):
            month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            months = [month_names[m] for m in sorted(cron.month.values)]
            parts.append(f"in {', '.join(months)}")

        # Day of week
        if cron.day_of_week.values != set(range(0, 7)):
            day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            days = [day_names[d] for d in sorted(cron.day_of_week.values)]
            parts.append(f"on {', '.join(days)}")

        return " ".join(parts)


# Convenience functions
def parse_cron(expression: str) -> CronExpression:
    """Parse a cron expression."""
    return CronParser.parse(expression)


def next_cron_run(expression: str, after: Optional[datetime] = None) -> datetime:
    """Get the next run time for a cron expression."""
    cron = CronParser.parse(expression)
    return cron.next_run(after)


def validate_cron(expression: str) -> Tuple[bool, Optional[str]]:
    """Validate a cron expression."""
    return CronParser.validate(expression)


def describe_cron(expression: str) -> str:
    """Get a human-readable description of a cron expression."""
    return CronParser.describe(expression)
