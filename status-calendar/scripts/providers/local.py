"""The calendar file used before a remote connection is configured."""

from calendar_store import Conflict, read_calendar, write_calendar


class LocalStore:
    source = "local"

    def __init__(self, directory):
        self.directory = directory

    def read(self):
        return read_calendar(self.directory)

    def commit(self, snapshot, expected_revision):
        # The backend holds the shared file lock across this read and replace.
        current = self.read()
        if expected_revision is None:
            if (self.directory / "calendar.json").exists():
                raise Conflict(current["revision"])
        elif current["revision"] != expected_revision:
            raise Conflict(current["revision"])
        write_calendar(self.directory, snapshot)
