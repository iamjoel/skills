from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from calendar_store import BODY_PARTS, body_parts_for, default_states, validate, workout_states_for
from save_edit import edited_snapshot


class WorkoutModelTest(unittest.TestCase):
    date = "2026-11-11"

    def setUp(self):
        self.old_run = {"id": "long-run", "kind": "run", "label": "跑步 ≥ 5 公里",
                        "color": "#286443", "emoji": "🏃"}
        self.custom = {"id": "yoga", "kind": "custom", "label": "瑜伽", "color": "#C27979", "emoji": "✨"}
        self.legacy = {"revision": 3, "states": [self.old_run, self.custom],
                       "days": {self.date: [{"stateId": "long-run", "emoji": ""}]}}

    def change(self, snapshot, **operation):
        return edited_snapshot(dict(operation, revision=snapshot["revision"], source="local"), snapshot, "local")

    def test_explicit_migration_keeps_ambiguous_distance_and_custom_history(self):
        original = deepcopy(self.legacy)
        states = workout_states_for(self.legacy)
        migrated = self.change(self.legacy, action="configure", states=states)
        self.assertEqual(self.legacy, original)
        self.assertEqual(migrated["days"], original["days"])
        self.assertEqual(states[-2], dict(self.old_run, label="跑步 ≥ 5 公里（旧记录，距离未细分）", archived=True))
        self.assertEqual(states[-1], self.custom)
        self.assertEqual(workout_states_for(migrated), states)
        self.assertEqual([s["id"] for s in states[:5]],
                         ["short-gym", "long-gym", "short-run", "mid-run", "over-ten-run"])
        self.assertEqual([p[0] for p in body_parts_for(states)], ["🐻", "🪽", "🏋️", "💪", "🧘", "🦵", "🍑"])
        self.assertEqual(body_parts_for(states), [list(p) for p in BODY_PARTS])
        self.assertNotIn("long-run", [s["id"] for s in workout_states_for(dict(self.legacy, days={}))])

    def test_daily_write_retains_archived_entry_only_on_its_original_date(self):
        state = self.change(self.legacy, action="configure", states=workout_states_for(self.legacy))
        old = state["days"][self.date]
        gym = {"stateId": "short-gym", "emoji": "", "parts": ["🐻", "🧘", "🍑"]}
        edited = self.change(state, action="day", date=self.date, entries=old + [gym])
        self.assertEqual(edited["days"][self.date], old + [gym])
        with self.assertRaises(ValueError):
            self.change(state, action="day", date="2026-11-12", entries=old)
        new_run = {"stateId": "over-ten-run", "emoji": ""}
        edited = self.change(edited, action="day", date=self.date, entries=[gym, new_run])
        self.assertEqual(edited["days"][self.date], [gym, new_run])
        self.assertEqual(self.change(edited, action="day", date=self.date, entries=[])["days"], {})

    def test_rejects_wrong_part_selections_in_real_day_edit(self):
        state = {"revision": 0, "states": default_states(), "days": {}}
        base = {"stateId": "short-gym", "emoji": ""}
        for entries in ([dict(base, parts=["🐻", "🪽", "💪", "🍑"])], [dict(base, parts=["🦵", "🦵"])],
                        [dict(base, parts=["🏃"])], [dict(base, parts="🍑")], [dict(base, parts=[{}])],
                        [dict(base, stateId="mid-run", parts=["🍑"])], [dict(base, stateId="short-run", emoji="💪")],
                        [base, dict(base, stateId="long-gym")]):
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                self.change(state, action="day", date=self.date, entries=entries)
        self.assertEqual(state["days"], {})

    def test_body_part_configuration_round_trips_and_drives_validation(self):
        states = default_states()
        states[0]["bodyParts"][0][0] = "🧸"
        gym = {"stateId": "long-gym", "emoji": "", "parts": ["🧸"]}
        state = {"revision": 0, "states": states, "days": {}}
        edited = self.change(state, action="day", date=self.date, entries=[gym])
        validate(edited)
        self.assertEqual(body_parts_for(edited["states"])[0], ["🧸", "胸部"])
        self.assertEqual(body_parts_for(default_states())[0], ["🐻", "胸部"])
        with self.assertRaises(ValueError):
            self.change(state, action="day", date=self.date, entries=[dict(gym, parts=["🐻"])])


if __name__ == "__main__":
    unittest.main()
