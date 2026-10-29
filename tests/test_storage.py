import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tusic.music import SHARPS, load_instruments
from tusic.practice import PracticeSession
from tusic.storage import (ScoreStore, Settings, SettingsStore, atomic_write_json,
                           default_config_directory, default_scores_directory)


class StorageTests(unittest.TestCase):
    def test_save_reload_and_score_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            settings = Settings(base / "my scores", "flats")
            store = SettingsStore(base / "config")
            store.save(settings)
            self.assertEqual(store.load(), (settings, None))
            session = PracticeSession(load_instruments()[0][0], 1)
            scores = ScoreStore(settings.scores_directory)
            path = scores.save(session)
            self.assertEqual(json.loads(path.read_text())["status"], "in_progress")
            session.submit(SHARPS[session.instrument.pitch_at(session.current)])
            self.assertEqual(scores.save(session), path)
            data = json.loads(path.read_text())
            self.assertEqual(data["status"], "completed")
            self.assertEqual(data["correct_count"], 1)
            self.assertEqual(data["schema_version"], 1)
            self.assertEqual(len(list(settings.scores_directory.glob("*.json"))), 1)

    def test_atomic_failure_preserves_previous_score(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "score.json"
            atomic_write_json(path, {"correct": 1})
            with patch("tusic.storage.os.replace", side_effect=PermissionError("read only")):
                with self.assertRaises(PermissionError):
                    atomic_write_json(path, {"correct": 2})
            self.assertEqual(json.loads(path.read_text()), {"correct": 1})
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_corrupt_settings_use_defaults_without_destroying_original(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory))
            for contents in ("{", "[]", '{"schema_version": 99}', '{"schema_version":1,"scores_directory":"relative"}'):
                store.path.write_text(contents, encoding="utf-8")
                settings, warning = store.load()
                self.assertIsNotNone(warning)
                self.assertEqual(settings.scores_directory, default_scores_directory())
                self.assertEqual(store.path.read_text(), contents)

    def test_changed_location_does_not_move_old_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            old, new = base / "old", base / "new"
            session = PracticeSession(load_instruments()[0][0], 1)
            original = ScoreStore(old).save(session)
            SettingsStore(base / "config").save(Settings(new))
            self.assertTrue(original.exists())
            self.assertEqual(list(new.iterdir()), [])

    def test_platform_defaults(self):
        # Simulate platform/environment choices using native absolute paths on either OS.
        base = Path(tempfile.gettempdir()).resolve()
        with patch("tusic.storage.sys.platform", "win32"), patch.dict(os.environ, {"APPDATA": str(base / "roaming"), "LOCALAPPDATA": str(base / "local")}):
            self.assertEqual(default_config_directory(), base / "roaming" / "Tusic")
            self.assertEqual(default_scores_directory(), base / "local" / "Tusic" / "scores")
        with patch("tusic.storage.sys.platform", "linux"), patch.dict(os.environ, {"XDG_CONFIG_HOME": str(base / "config"), "XDG_DATA_HOME": str(base / "data")}):
            self.assertEqual(default_config_directory(), base / "config" / "tusic")
            self.assertEqual(default_scores_directory(), base / "data" / "tusic" / "scores")
        with patch("tusic.storage.sys.platform", "linux"), patch.dict(os.environ, {"XDG_CONFIG_HOME": "relative", "XDG_DATA_HOME": "relative"}):
            self.assertEqual(default_config_directory(), Path.home() / ".config" / "tusic")
            self.assertEqual(default_scores_directory(), Path.home() / ".local" / "share" / "tusic" / "scores")


if __name__ == "__main__":
    unittest.main()
