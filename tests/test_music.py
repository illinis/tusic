import json
from pathlib import Path
import tempfile
import unittest

from tusic.music import Instrument, Position, load_instruments, note_name, parse_note


class MusicTests(unittest.TestCase):
    def setUp(self):
        self.instruments = {instrument.id: instrument for instrument in load_instruments()[0]}
        self.guitar = self.instruments["guitar_standard"]

    def test_bundled_four_string_instruments(self):
        cases = (
            ("violin_standard", ("G3", "D4", "A4", "E5"), ("E", "A", "D", "G"), False),
            ("cavaquinho_brazilian", ("D4", "G4", "B4", "D5"), ("D", "B", "G", "D"), True),
        )
        for identifier, tuning, top_to_bottom, fretted in cases:
            with self.subTest(instrument=identifier):
                instrument = self.instruments[identifier]
                self.assertEqual(instrument.string_count, 4)
                self.assertEqual(instrument.tuning, tuning)
                self.assertEqual(instrument.fretted, fretted)
                self.assertEqual(len(instrument.positions(0, 12)), 52)
                for string, note in enumerate(top_to_bottom, 1):
                    self.assertEqual(instrument.pitch_at(Position(string, 0)), parse_note(note))
                    self.assertEqual(instrument.pitch_at(Position(string, 12)), parse_note(note))
                self.assertEqual(instrument.pitch_at(Position(1, 1)), (parse_note(top_to_bottom[0]) + 1) % 12)
        self.assertEqual(self.instruments["violin_standard"].markers, ())
        self.assertIn(12, self.instruments["cavaquinho_brazilian"].double_markers)

    def test_instrument_specific_position_labels(self):
        violin = self.instruments["violin_standard"]
        self.assertEqual(violin.range_label, "Semitone range")
        self.assertEqual(violin.position_label(0), "open string")
        self.assertEqual(violin.position_label(1), "1 semitone above open")
        self.assertEqual(violin.position_label(7), "7 semitones above open")
        self.assertEqual(self.guitar.range_label, "Fret range")
        self.assertEqual(self.guitar.position_label(7), "fret 7")

    def test_standard_tuning_and_octave_repeat(self):
        for string_number, note in enumerate(("E", "B", "G", "D", "A", "E"), 1):
            with self.subTest(string=string_number):
                self.assertEqual(self.guitar.pitch_at(Position(string_number, 0)), parse_note(note))
                self.assertEqual(self.guitar.pitch_at(Position(string_number, 12)), parse_note(note))

    def test_reference_notes(self):
        for string_number, fret, note in ((6, 3, "G"), (5, 3, "C"), (4, 5, "G"),
                                           (3, 4, "B"), (2, 1, "C"), (1, 9, "C#")):
            with self.subTest(string=string_number, fret=fret):
                self.assertEqual(self.guitar.pitch_at(Position(string_number, fret)), parse_note(note))

    def test_enharmonic_and_unicode_answers(self):
        for left, right in (("C#", "Db"), ("d#", "e♭"), ("F♯", "gb"), ("B#", "C"),
                            ("Cb", "B"), ("Fb", "E"), ("E#", "F"), (" bb ", "A#")):
            with self.subTest(left=left, right=right):
                self.assertEqual(parse_note(left), parse_note(right))
        for pitch in range(12):
            for spelling in ("sharps", "flats"):
                self.assertEqual(parse_note(note_name(pitch, spelling)), pitch)

    def test_invalid_notes_do_not_silently_match(self):
        for text in ("", "H", "C4", "C##", "C/Db", "1", "A B", "hello"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_note(text)

    def test_invalid_positions_and_ranges(self):
        for position in (Position(0, 0), Position(7, 0), Position(1, -1), Position(1, 13)):
            with self.assertRaises(ValueError):
                self.guitar.pitch_at(position)
        for first, last in ((-1, 12), (6, 2), (0, 13)):
            with self.assertRaises(ValueError):
                self.guitar.positions(first, last)

    def test_custom_instrument_changes_tuning_strings_and_markers(self):
        with tempfile.TemporaryDirectory() as directory:
            custom = {"id": "viola", "name": "Viola", "tuning": ["C3", "G3", "D4", "A4"],
                      "fret_count": 12, "markers": [], "double_markers": [], "fretted": False}
            Path(directory, "viola.json").write_text(json.dumps(custom), encoding="utf-8")
            instruments, warnings = load_instruments(Path(directory))
            self.assertEqual(warnings, [])
            viola = next(item for item in instruments if item.id == "viola")
            self.assertEqual(viola.string_count, 4)
            self.assertFalse(viola.fretted)
            self.assertEqual(viola.pitch_at(Position(4, 0)), parse_note("C"))
            self.assertEqual(viola.markers, ())

    def test_bad_definitions_do_not_hide_bundled_guitar(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "broken.json").write_text("{", encoding="utf-8")
            Path(directory, "duplicate.json").write_text(json.dumps(self.guitar.to_dict()), encoding="utf-8")
            instruments, warnings = load_instruments(Path(directory))
            self.assertEqual({item.id for item in instruments}, set(self.instruments))
            self.assertEqual(len(warnings), 2)
        for field, value in (("tuning", []), ("tuning", ["Q2"]), ("fret_count", True),
                             ("markers", [13]), ("fretted", "false")):
            data = self.guitar.to_dict()
            data[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                Instrument.from_dict(data)


if __name__ == "__main__":
    unittest.main()
