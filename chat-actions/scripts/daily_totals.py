import sqlite3
from contextlib import closing
from decimal import Decimal, InvalidOperation
from pathlib import Path


def format_total(total: Decimal) -> str:
    value = format(total, "f")
    return value.rstrip("0").rstrip(".") if "." in value else value


def read_group(connection: sqlite3.Connection, group: str, day: str) -> dict[str, str]:
    rows = connection.execute(
        "SELECT variable, amount FROM increments WHERE group_name = ? AND day = ? ORDER BY rowid",
        (group, day),
    )
    totals = {}
    for variable, amount in rows:
        increment = Decimal(amount)
        if increment == 0:
            totals[variable] = Decimal(0)
        else:
            totals[variable] = totals.get(variable, Decimal(0)) + increment
    return {variable: format_total(total) for variable, total in totals.items()}


def read_totals(path: Path, group: str, day: str) -> dict[str, str]:
    if not path.is_file():
        return {}
    uri = f"{path.resolve().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'increments'"
        ).fetchone()
        return read_group(connection, group, day) if table else {}


def record_increment(
    path: Path,
    group: str,
    day: str,
    variable: str,
    amount: str,
    request_id: str,
) -> tuple[bool, str]:
    try:
        increment = Decimal(amount)
        numeric_value = float(increment)
    except (InvalidOperation, OverflowError, ValueError) as error:
        raise ValueError("累加值必须是正数。") from error
    if not 0 < numeric_value < float("inf"):
        raise ValueError("累加值必须是正数。")

    return _record_event(path, group, day, variable, str(increment), request_id)


def record_reset(
    path: Path,
    group: str,
    day: str,
    variable: str,
    request_id: str,
) -> tuple[bool, str]:
    return _record_event(path, group, day, variable, "0", request_id)


def _record_event(
    path: Path,
    group: str,
    day: str,
    variable: str,
    amount: str,
    request_id: str,
) -> tuple[bool, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS increments (
                request_id TEXT PRIMARY KEY,
                group_name TEXT NOT NULL,
                day TEXT NOT NULL,
                variable TEXT NOT NULL,
                amount TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS increments_by_day
            ON increments (group_name, day, variable)
        """)
        event = connection.execute("""
            INSERT INTO increments (request_id, group_name, day, variable, amount)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(request_id) DO NOTHING
        """, (request_id, group, day, variable, amount))
        total = read_group(connection, group, day).get(variable, "0")
        return event.rowcount == 1, total
