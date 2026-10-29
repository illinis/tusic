import json
import random
import unittest

from tusic.exercises import EXERCISES, ExerciseSession
from tusic.music import Position, load_instruments
from tusic.theory import (KEYS, SCALES, frequency, midi_name, normalize_note, note_midi,
                          parse_notes, pitch_class, scale_notes, spelled_above, triad)


class TheoryTests(unittest.TestCase):
    def test_known_scales_and_correct_spelling(self):
        self.assertEqual(scale_notes("G", "Major"), ("G", "A", "B", "C", "D", "E", "F#"))
        self.assertEqual(scale_notes("F", "Natural minor"), ("F", "G", "Ab", "Bb", "C", "Db", "Eb"))
        self.assertEqual(scale_notes("C#", "Major"), ("C#", "D#", "E#", "F#", "G#", "A#", "B#"))
        self.assertEqual(scale_notes("A", "Minor pentatonic"), ("A", "C", "D", "E", "G"))
        for root in KEYS:
            for kind, (offsets, letters) in SCALES.items():
                with self.subTest(root=root, kind=kind):
                    notes = scale_notes(root, kind)
                    self.assertEqual(len({note[0] for note in notes}), len(notes))
                    self.assertEqual(tuple((pitch_class(n)-pitch_class(root)) % 12 for n in notes), offsets)

    def test_intervals_distinguish_enharmonic_spelling(self):
        self.assertEqual(spelled_above("C", 3, 6), "F#")
        self.assertEqual(spelled_above("C", 4, 6), "Gb")
        self.assertEqual(spelled_above("Gb", 4, 6), "Dbb")
        self.assertEqual(spelled_above("F#", 6, 11), "E#")
        self.assertEqual(note_midi("B#", 4), 72)
        self.assertEqual(note_midi("Cb", 4), 59)

    def test_accidentals_input_and_octaves(self):
        self.assertEqual(normalize_note("f𝄪"), "F##")
        self.assertEqual(parse_notes("bb, D; F♯"), ("Bb", "D", "F#"))
        for value in ("", "H", "C4", "Cb#", "Fxxx"):
            with self.assertRaises(ValueError):
                normalize_note(value)
        self.assertEqual(midi_name(69), "A4")
        self.assertEqual(frequency(69), 440)

    def test_diatonic_chords(self):
        self.assertEqual(triad("D", "Major", 2), (("E", "G", "B"), "minor", "ii"))
        self.assertEqual(triad("D", "Major", 5), (("A", "C#", "E"), "major", "V"))
        self.assertEqual(triad("C", "Major", 7), (("B", "D", "F"), "diminished", "vii°"))
        self.assertEqual(triad("A", "Natural minor", 5), (("E", "G", "B"), "minor", "v"))


class ExerciseTests(unittest.TestCase):
    def setUp(self):
        self.instrument = next(i for i in load_instruments()[0] if i.id == "guitar_standard")

    def test_every_exercise_scores_and_serializes(self):
        for identifier in EXERCISES:
            with self.subTest(exercise=identifier):
                session = ExerciseSession(identifier, 6, instrument=self.instrument, rng=random.Random(13))
                for _ in range(6):
                    question = session.current
                    value = question.expected
                    if question.kind == "notes":
                        value = " ".join(value)
                    if question.kind == "chord":
                        value = (" ".join(value[0]), value[1])
                    if question.kind == "voice":
                        session.record_result(True, "On pitch", {"target_midi": value})
                    else:
                        self.assertTrue(session.submit(value)["correct"])
                    session.advance()
                record = json.loads(json.dumps(session.to_dict()))
                self.assertEqual(record["status"], "completed")
                self.assertEqual(record["correct_count"], 6)
                self.assertEqual(record["exercise_id"], identifier)
                self.assertIn("expected_answer", record["answers"][0])
                with self.assertRaises(ValueError):
                    session.record_result(True, "duplicate")

    def test_scale_spelling_wrong_order_and_repeated_tonic(self):
        session = ExerciseSession("scales", 3, {"key": "G"})
        with self.assertRaises(ValueError):
            session.submit("G A")
        self.assertEqual(session.answers, [])
        self.assertFalse(session.submit("G A B C D E Gb")["correct"])
        session.advance()
        self.assertTrue(session.submit("G A B C D E F# G")["correct"])
        session.advance()
        self.assertFalse(session.submit("G B A C D E F#")["correct"])

    def test_mapping_requires_all_and_only_scale_positions(self):
        session = ExerciseSession("scale_mapping", 2, {"key": "C", "first": 0, "last": 1}, self.instrument)
        expected = session.current.expected
        self.assertIn(Position(2, 1), expected)  # C on the B string.
        self.assertNotIn(Position(5, 1), expected)  # Bb is outside C major.
        self.assertFalse(session.submit(set(expected) | {Position(5, 1)})["correct"])
        session.advance()
        self.assertFalse(session.submit(set(expected) - {Position(2, 1)})["correct"])

    def test_ear_sequence_has_tonic_chord_reference_and_target(self):
        session = ExerciseSession("ear_training", 1, {"key": "C"}, rng=random.Random(3))
        question = session.current
        self.assertEqual(question.audio[0][0], [60, 64, 67])
        self.assertEqual(question.audio[2][0], [60])
        self.assertEqual(question.audio[-1][0], [60 + SCALES["Major"][0][int(question.expected)-1]])

    def test_voice_random_range_and_single_note(self):
        session = ExerciseSession("singing", 30, {"low_midi": 60, "high_midi": 64}, rng=random.Random(1))
        values = [question.expected for question in session.questions]
        self.assertEqual(set(values[:5]), set(range(60, 65)))
        self.assertTrue(all(60 <= value <= 64 for value in values))
        self.assertTrue(all(a != b for a, b in zip(values, values[1:])))
        only = ExerciseSession("singing", 3, {"low_midi": 60, "high_midi": 60})
        self.assertEqual([q.expected for q in only.questions], [60, 60, 60])
        with self.assertRaises(ValueError):
            ExerciseSession("singing", 2, {"low_midi": 72, "high_midi": 48})

    def test_partial_scores_and_skip(self):
        session = ExerciseSession("intervals", 5)
        session.record_result(False, "Skipped", {"skipped": True})
        session.finish()
        self.assertEqual(session.to_dict()["status"], "abandoned")
        self.assertEqual(session.correct_count, 0)


if __name__ == "__main__":
    unittest.main()
