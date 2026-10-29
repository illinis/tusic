import random
import unittest

from tusic.music import FLATS, SHARPS, load_instruments
from tusic.practice import PracticeSession


class PracticeTests(unittest.TestCase):
    def setUp(self):
        self.guitar = next(instrument for instrument in load_instruments()[0]
                           if instrument.id == "guitar_standard")

    def session(self, count=20, first=0, last=12):
        return PracticeSession(self.guitar, count, first, last, random.Random(42))

    def test_covers_all_78_positions_before_repeating(self):
        session = self.session(160)
        self.assertEqual(len(session.questions), 160)
        self.assertEqual(len(set(session.questions[:78])), 78)
        self.assertEqual(len(set(session.questions[78:156])), 78)
        self.assertNotEqual(session.questions[77], session.questions[78])
        self.assertNotEqual(session.questions[155], session.questions[156])

    def test_range_and_single_fret_matches(self):
        for first, last in ((0, 0), (5, 7), (12, 12)):
            session = self.session(500, first, last)
            self.assertTrue(all(first <= position.fret <= last for position in session.questions))

    def test_invalid_counts_and_ranges(self):
        for count in (0, -1, 501, 1.5, True):
            with self.assertRaises(ValueError):
                self.session(count)
        with self.assertRaises(ValueError):
            self.session(5, 8, 3)

    def test_scoring_invalid_answer_duplicate_and_completion(self):
        session = self.session(2)
        with self.assertRaises(ValueError):
            session.advance()
        with self.assertRaises(ValueError):
            session.submit("H")
        self.assertEqual(len(session.answers), 0)
        correct = session.instrument.pitch_at(session.current)
        self.assertTrue(session.submit(FLATS[correct])["correct"])
        with self.assertRaises(ValueError):
            session.submit(SHARPS[correct])
        self.assertTrue(session.advance())
        correct = session.instrument.pitch_at(session.current)
        self.assertFalse(session.submit(SHARPS[(correct + 1) % 12])["correct"])
        self.assertFalse(session.advance())
        result = session.to_dict()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["correct_count"], 1)
        self.assertEqual(result["accuracy_percent"], 50.0)
        self.assertEqual(result["total_answered"], 2)
        self.assertIsNotNone(result["ended_at"])
        self.assertEqual(result["instrument"]["tuning"], ["E2", "A2", "D3", "G3", "B3", "E4"])
        self.assertIn("response_seconds", result["answers"][0])
        session.finish("abandoned")
        self.assertEqual(session.status, "completed")

    def test_partial_and_empty_matches(self):
        session = self.session(10)
        session.submit(SHARPS[session.instrument.pitch_at(session.current)])
        session.finish()
        self.assertEqual(session.status, "abandoned")
        self.assertEqual(session.to_dict()["total_answered"], 1)
        self.assertEqual(session.accuracy, 100)
        self.assertFalse(session.advance())
        empty = self.session()
        empty.finish()
        self.assertEqual(empty.accuracy, 0)

    def test_cannot_finish_early_as_completed(self):
        with self.assertRaises(ValueError):
            self.session().finish("completed")


if __name__ == "__main__":
    unittest.main()
