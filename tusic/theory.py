"""Spelled intervals, scales and diatonic triads. No network or audio required."""

import re

from .music import NATURALS, SHARPS

LETTERS = "CDEFGAB"
KEYS = ("C", "G", "D", "A", "E", "B", "F#", "F", "Bb", "Eb", "Ab", "Db", "Gb")
SCALES = {
    "Major": ((0, 2, 4, 5, 7, 9, 11), (0, 1, 2, 3, 4, 5, 6)),
    "Natural minor": ((0, 2, 3, 5, 7, 8, 10), (0, 1, 2, 3, 4, 5, 6)),
    "Major pentatonic": ((0, 2, 4, 7, 9), (0, 1, 2, 4, 5)),
    "Minor pentatonic": ((0, 3, 5, 7, 10), (0, 2, 3, 4, 6)),
}
INTERVALS = {
    "Minor second": (1, 1), "Major second": (1, 2),
    "Minor third": (2, 3), "Major third": (2, 4),
    "Perfect fourth": (3, 5), "Augmented fourth": (3, 6),
    "Diminished fifth": (4, 6), "Perfect fifth": (4, 7),
    "Minor sixth": (5, 8), "Major sixth": (5, 9),
    "Minor seventh": (6, 10), "Major seventh": (6, 11),
    "Perfect octave": (7, 12),
}
BASIC_INTERVALS = ("Minor third", "Major third", "Perfect fourth", "Perfect fifth", "Perfect octave")


def normalize_note(text: str) -> str:
    text = text.strip().replace("♯", "#").replace("♭", "b").replace("𝄪", "##").replace("𝄫", "bb")
    match = re.fullmatch(r"([A-Ga-g])([#bBxX]{0,2})", text)
    if not match:
        raise ValueError("Use note names without octave numbers, such as C, F#, or Bb.")
    letter, accidental = match.groups()
    accidental = accidental.lower().replace("x", "##")
    if accidental not in ("", "#", "##", "b", "bb"):
        raise ValueError("Use a natural, sharp, flat, double sharp, or double flat.")
    return letter.upper() + accidental


def pitch_class(note: str) -> int:
    name = normalize_note(note)
    return (NATURALS[name[0]] + name.count("#") - name.count("b")) % 12


def spelled_above(root: str, letter_steps: int, semitones: int) -> str:
    root = normalize_note(root)
    letter = LETTERS[(LETTERS.index(root[0]) + letter_steps) % 7]
    offset = ((pitch_class(root) + semitones - NATURALS[letter] + 6) % 12) - 6
    if abs(offset) > 2:
        raise ValueError("This key would require accidentals beyond double sharps/flats.")
    return letter + ("#" * offset if offset > 0 else "b" * -offset)


def scale_notes(root: str, kind: str) -> tuple[str, ...]:
    semitones, letters = SCALES[kind]
    return tuple(spelled_above(root, step, distance) for distance, step in zip(semitones, letters))


def parse_notes(text: str) -> tuple[str, ...]:
    parts = re.split(r"[\s,;]+", text.strip())
    if not text.strip():
        raise ValueError("Enter the notes separated by spaces, for example G A B C D E F#.")
    return tuple(normalize_note(part) for part in parts if part)


def triad(root: str, kind: str, degree: int) -> tuple[tuple[str, ...], str, str]:
    if kind not in ("Major", "Natural minor") or not 1 <= degree <= 7:
        raise ValueError("Triads use degrees 1–7 of major or natural minor.")
    scale = scale_notes(root, kind)
    notes = tuple(scale[(degree - 1 + step) % 7] for step in (0, 2, 4))
    shape = tuple((pitch_class(note) - pitch_class(notes[0])) % 12 for note in notes)
    quality = {(0, 4, 7): "major", (0, 3, 7): "minor", (0, 3, 6): "diminished"}[shape]
    roman = ("I", "II", "III", "IV", "V", "VI", "VII")[degree - 1]
    if quality != "major":
        roman = roman.lower()
    if quality == "diminished":
        roman += "°"
    return notes, quality, roman


def midi_name(midi: int) -> str:
    return f"{SHARPS[midi % 12]}{midi // 12 - 1}"


def frequency(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def note_midi(name: str, octave: int = 4) -> int:
    name = normalize_note(name)
    # Keep B#4 in octave 5 and Cb4 in octave 3.
    return 12 * (octave + 1) + NATURALS[name[0]] + name.count("#") - name.count("b")
