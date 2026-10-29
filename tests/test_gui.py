"""Opt-in Tk integration tests. On Linux use xvfb-run or a graphical session."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tusic.music import FLATS, SHARPS, Position


@unittest.skipUnless(os.environ.get("TUSIC_TEST_GUI") == "1", "Set TUSIC_TEST_GUI=1 to run Tk integration tests")
class GuiTests(unittest.TestCase):
    def setUp(self):
        from tusic.ui import TusicApp
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.app = TusicApp(self.base / "config", self.base / "scores")
        self.app.withdraw()
        self.app.update()

    def tearDown(self):
        self.app.destroy()
        self.temp.cleanup()

    def start(self, count="2"):
        self.app.show_setup()
        self.app.count_var.set(count)
        self.app.start_match()
        self.app.update()

    def test_complete_match_and_review(self):
        self.start()
        self.assertEqual(self.app.view, "quiz")
        self.assertEqual(str(self.app.notebook.tab(self.app.settings_tab, "state")), "disabled")
        pitch = self.app.session.instrument.pitch_at(self.app.session.current)
        self.app.submit_answer(FLATS[pitch])
        self.assertEqual(self.app.session.correct_count, 1)
        self.app.next_question()
        pitch = self.app.session.instrument.pitch_at(self.app.session.current)
        self.app.submit_answer(SHARPS[(pitch + 1) % 12])
        self.app.next_question()
        self.assertEqual(self.app.view, "results")
        data = json.loads(self.app.saved_path.read_text())
        self.assertEqual((data["correct_count"], data["accuracy_percent"]), (1, 50))
        self.assertEqual(data["status"], "completed")
        self.assertEqual(str(self.app.notebook.tab(self.app.settings_tab, "state")), "normal")

    def test_invalid_setup_and_invalid_answer(self):
        self.app.show_setup()
        self.app.count_var.set("oops")
        with patch("tusic.ui.messagebox.showerror") as error:
            self.app.start_match()
            error.assert_called_once()
        self.assertEqual(self.app.view, "setup")
        self.start()
        self.app.submit_answer("H")
        self.assertEqual(len(self.app.session.answers), 0)
        self.assertEqual(str(self.app.next_button["state"]), "disabled")

    def test_save_failure_blocks_advance_and_can_be_retried(self):
        self.start()
        pitch = self.app.session.instrument.pitch_at(self.app.session.current)
        with patch.object(self.app.score_store, "save", side_effect=PermissionError("test failure")), patch("tusic.ui.messagebox.showerror"):
            self.app.submit_answer(SHARPS[pitch])
            self.assertTrue(self.app.save_pending)
            self.app.next_question()
            self.assertEqual(self.app.session.index, 0)
        self.app.next_question()
        self.assertFalse(self.app.save_pending)
        self.assertEqual(self.app.session.index, 1)

    def test_end_early_is_saved(self):
        self.start()
        pitch = self.app.session.instrument.pitch_at(self.app.session.current)
        self.app.submit_answer(SHARPS[pitch])
        with patch("tusic.ui.messagebox.askyesno", return_value=True):
            self.app.end_match()
        self.assertEqual(self.app.view, "results")
        data = json.loads(self.app.saved_path.read_text())
        self.assertEqual((data["status"], data["total_answered"]), ("abandoned", 1))

    def test_settings_persist_and_future_match_uses_new_folder(self):
        self.app.folder_var.set(str(self.base / "other scores"))
        self.app.spelling_var.set("flats")
        self.app.save_settings()
        settings, warning = self.app.settings_store.load()
        self.assertIsNone(warning)
        self.assertEqual(settings.spelling, "flats")
        self.start("1")
        self.assertEqual(self.app.saved_path.parent, self.base / "other scores")
        self.assertEqual(self.app.answer_buttons[1]["text"], "Db")

    def test_new_instruments_render_score_and_save(self):
        self.app.show_setup()
        self.assertEqual(self.app.instruments[self.app.instrument_choice.current()].id, "guitar_standard")
        for identifier, open_notes, fretted in (
            ("violin_standard", ("E", "A", "D", "G"), False),
            ("cavaquinho_brazilian", ("D", "B", "G", "D"), True),
        ):
            with self.subTest(instrument=identifier):
                self.app.show_setup()
                index = next(i for i, item in enumerate(self.app.instruments) if item.id == identifier)
                self.app.instrument_choice.current(index)
                self.app.instrument_changed()
                self.assertEqual(self.app.range_label["text"], "Fret range" if fretted else "Semitone range")
                self.app.count_var.set("4")
                self.app.last_var.set("0")
                self.app.start_match()
                self.app.board.redraw()
                board = self.app.board
                lines = [item for item in board.find_all() if board.type(item) == "line"]
                horizontal = [item for item in lines if board.coords(item)[1] == board.coords(item)[3]]
                guides = [item for item in lines if board.itemcget(item, "dash")]
                self.assertEqual(len(horizontal), 4)
                self.assertEqual(len(guides), 0 if fretted else 12)
                if not fretted:
                    # A highlighted semitone must sit on its guide, rather than between guides.
                    for step in (1, 7, 12):
                        board.set_question(Position(1, step))
                        dot = next(item for item in board.find_all() if board.type(item) == "oval")
                        x1, _, x2, _ = board.coords(dot)
                        guide = [item for item in board.find_all()
                                 if board.type(item) == "line" and board.itemcget(item, "dash")][step - 1]
                        self.assertAlmostEqual((x1 + x2) / 2, board.coords(guide)[0])
                    board.set_question(self.app.session.current)
                for _ in range(4):
                    self.app.submit_answer(open_notes[self.app.session.current.string_number - 1])
                    self.app.next_question()
                self.assertEqual(self.app.view, "results")
                data = json.loads(self.app.saved_path.read_text())
                self.assertEqual(data["instrument"]["id"], identifier)
                self.assertEqual(data["instrument"]["fretted"], fretted)
                self.assertEqual((data["correct_count"], data["status"]), (4, "completed"))


if __name__ == "__main__":
    unittest.main()
