"""GUI workflows with simulated local audio; never opens a real microphone."""

import json
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from tusic.exercises import EXERCISES
from tusic.theory import frequency


@unittest.skipUnless(os.environ.get("TUSIC_TEST_GUI") == "1", "Set TUSIC_TEST_GUI=1 to run Tk integration tests")
class LearningGuiTests(unittest.TestCase):
    def setUp(self):
        from tusic.ui import TusicApp
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.app = TusicApp(self.root / "config", self.root / "scores")
        self.app.withdraw()
        self.backend = Mock()
        self.backend.devices.return_value = [(1, "Test device")]
        self.backend.play.return_value = 0
        self.app.audio_backend = self.backend
        self.app.update()

    def tearDown(self):
        self.app.stop_media()
        self.app.destroy()
        self.temp.cleanup()

    def start(self, identifier, count="1", **values):
        self.app.show_learning_setup(identifier)
        self.app.learning_vars["count"].set(count)
        for key, value in values.items():
            self.app.learning_vars[key].set(str(value))
        self.app.start_learning_match()
        self.app.update_idletasks()
        self.assertEqual(self.app.view, "quiz")

    def cancel_poll(self):
        if self.app.microphone_timer is not None:
            self.app.after_cancel(self.app.microphone_timer)
            self.app.microphone_timer = None

    def test_written_exercises_complete_and_save(self):
        for identifier in ("intervals", "scales", "scale_degrees", "diatonic_chords"):
            with self.subTest(exercise=identifier):
                self.start(identifier, key="G")
                question = self.app.session.current
                if question.kind == "notes":
                    self.app.answer_var.set(" ".join(question.expected))
                    self.app.submit_learning_answer()
                elif question.kind == "chord":
                    self.app.answer_var.set(" ".join(question.expected[0]))
                    self.app.quality_var.set(question.expected[1])
                    self.app.submit_learning_answer()
                else:
                    self.app.submit_learning_answer(question.expected)
                self.app.next_question()
                self.assertEqual(self.app.view, "results")
                data = json.loads(self.app.saved_path.read_text())
                self.assertEqual((data["exercise_id"], data["correct_count"]), (identifier, 1))

    def test_scale_mapping_clicks_and_feedback(self):
        self.start("scale_mapping", key="C", last="3")
        expected = self.app.session.current.expected
        for position in expected:
            x, y = self.app.board.centres[position]
            self.app.board.select_at(SimpleNamespace(x=x, y=y))
        self.assertEqual(self.app.board.selected, set(expected))
        self.app.submit_learning_answer()
        self.assertEqual(self.app.session.correct_count, 1)
        self.assertEqual(self.app.board.expected, expected)
        self.app.next_question()
        self.assertEqual(self.app.view, "results")

    def test_ear_training_requires_playback_and_can_replay(self):
        self.start("ear_training")
        self.app.submit_learning_answer(self.app.session.current.expected)
        self.assertEqual(self.app.session.answers, [])
        self.app.play_question_audio()
        self.assertFalse(self.app.heard_audio)
        deadline = time.monotonic() + 2
        while not self.app.heard_audio and time.monotonic() < deadline:
            self.app.update()
            time.sleep(0.01)
        self.assertTrue(self.app.heard_audio)
        self.backend.play.assert_called_once()
        self.app.submit_learning_answer(self.app.session.current.expected)
        self.assertEqual(self.app.session.correct_count, 1)
        self.app.next_question()
        self.assertEqual(self.app.view, "results")

    def test_voice_passes_sustained_correct_pitch_and_closes_mic(self):
        self.start("singing", low_note="A3", high_note="A3")
        microphone = Mock(active=True)
        samples = 0.3 * np.sin(2 * np.pi * frequency(57) * np.arange(6720) / 48000)
        microphone.read.return_value = (samples, 48000, 0.1, "")
        self.backend.microphone.return_value = microphone
        self.app.start_listening()
        for _ in range(10):
            self.cancel_poll()
            self.app.poll_voice()
            if self.app.session.answered_current:
                break
        self.assertTrue(self.app.session.answered_current)
        self.assertEqual(self.app.session.correct_count, 1)
        microphone.close.assert_called_once()
        self.assertIsNone(self.app.microphone)
        self.app.next_question()
        data = json.loads(self.app.saved_path.read_text())
        self.assertEqual(data["answers"][0]["target_midi"], 57)
        self.assertNotIn("samples", data["answers"][0])

    def test_voice_wrong_octave_times_out_and_silence_does_not_pass(self):
        for samples in (np.zeros(6720), 0.3 * np.sin(2*np.pi*440*np.arange(6720)/48000)):
            self.start("singing", low_note="A3", high_note="A3")
            microphone = Mock(active=True)
            microphone.read.return_value = (samples, 48000, 0.1, "")
            self.backend.microphone.return_value = microphone
            self.app.start_listening()
            self.cancel_poll()
            self.app.voice_started -= 11
            self.app.poll_voice()
            self.assertEqual(self.app.session.correct_count, 0)
            self.assertEqual(len(self.app.session.answers), 1)
            microphone.close.assert_called_once()

    def test_reference_cannot_be_captured_and_stop_discards_input(self):
        self.start("singing")
        self.app.play_question_audio()
        self.app.start_listening()
        self.backend.microphone.assert_not_called()
        self.app.stop_media()
        microphone = Mock(active=True)
        self.backend.microphone.return_value = microphone
        self.app.start_listening()
        self.app.stop_listening()
        microphone.close.assert_called_once()
        self.assertEqual(self.app.session.answers, [])
        self.assertIsNone(self.app.microphone_timer)

    def test_microphone_errors_and_missing_devices_are_recoverable(self):
        self.backend.devices.return_value = []
        self.app.show_learning_setup("singing")
        with patch("tusic.learning_ui.messagebox.showerror") as error:
            self.app.start_learning_match()
            error.assert_called_once()
        self.assertIsNone(self.app.session)
        self.backend.devices.return_value = [(1, "Test device")]
        self.start("singing")
        self.backend.microphone.side_effect = RuntimeError("permission denied")
        with patch("tusic.learning_ui.messagebox.showerror") as error:
            self.app.start_listening()
            error.assert_called_once()
        self.assertIsNone(self.app.microphone)
        self.assertEqual(self.app.session.answers, [])

    def test_new_session_save_failure_retry_and_skip(self):
        self.start("scales", count="2", key="G")
        self.app.answer_var.set("G A B C D E F#")
        with patch.object(self.app.score_store, "save", side_effect=PermissionError("test")), patch("tusic.ui.messagebox.showerror"):
            self.app.submit_learning_answer()
            self.app.next_question()
            self.assertEqual(self.app.session.index, 0)
        self.app.next_question()
        self.app.skip_learning_question()
        self.app.next_question()
        self.assertEqual(self.app.view, "results")
        self.assertEqual(self.app.session.correct_count, 1)

    def test_end_match_stops_recording_and_saves_partial(self):
        self.start("singing", count="2")
        microphone = Mock(active=True)
        self.backend.microphone.return_value = microphone
        self.app.start_listening()
        with patch("tusic.ui.messagebox.askyesno", return_value=True):
            self.app.end_match()
        microphone.close.assert_called_once()
        self.assertEqual(self.app.view, "results")
        self.assertEqual(json.loads(self.app.saved_path.read_text())["status"], "abandoned")


if __name__ == "__main__":
    unittest.main()
