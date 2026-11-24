import sqlite3
from contextlib import closing
from pathlib import Path


def read_variable_values(path: Path, group: str) -> dict[str, str]:
    if not path.is_file():
        return {}
    uri = f"{path.resolve().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'shared_variables'"
        ).fetchone()
        if not table:
            return {}
        rows = connection.execute(
            "SELECT name, value FROM shared_variables WHERE group_name = ?", (group,)
        )
        return dict(rows)


def save_variable_values(path: Path, group: str, values: dict[str, str]) -> None:
    if not values:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS shared_variables (
                group_name TEXT NOT NULL,
                name TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (group_name, name)
            )
        """)
        connection.executemany("""
            INSERT INTO shared_variables (group_name, name, value)
            VALUES (?, ?, ?)
            ON CONFLICT(group_name, name) DO UPDATE SET value = excluded.value
        """, ((group, name, value) for name, value in values.items()))
