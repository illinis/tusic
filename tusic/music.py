"""Notes and instrument definitions, independent of the user interface."""

from dataclasses import dataclass
from importlib import resources
import json
from pathlib import Path
import re

SHARPS = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
FLATS = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")
NATURALS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def parse_note(text: str) -> int:
    """Accept a note letter with an optional sharp/flat, including Unicode."""
    cleaned = text.strip().replace("♯", "#").replace("♭", "b")
    match = re.fullmatch(r"([A-Ga-g])([#bB]?)", cleaned)
    if not match:
        raise ValueError("Enter a note such as C, F#, or Bb (no octave number).")
    letter, accidental = match.groups()
    offset = 1 if accidental == "#" else -1 if accidental else 0
    return (NATURALS[letter.upper()] + offset) % 12


def note_name(pitch_class: int, spelling: str = "sharps") -> str:
    return (FLATS if spelling == "flats" else SHARPS)[pitch_class % 12]


def note_names(pitch_class: int) -> str:
    sharp, flat = SHARPS[pitch_class % 12], FLATS[pitch_class % 12]
    return sharp if sharp == flat else f"{sharp} / {flat}"


@dataclass(frozen=True)
class Position:
    string_number: int  # 1 is the highest/thinnest string, at the top of the diagram.
    fret: int


@dataclass(frozen=True)
class Instrument:
    id: str
    name: str
    tuning: tuple[str, ...]  # Physical string order, bottom to top in the diagram.
    fret_count: int
    markers: tuple[int, ...]
    double_markers: tuple[int, ...]
    fretted: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "Instrument":
        if not isinstance(data, dict):
            raise ValueError("An instrument definition must be a JSON object.")
        identifier, name = data.get("id"), data.get("name")
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9_-]+", identifier):
            raise ValueError("Instrument id must use lowercase letters, digits, '_' or '-'.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("An instrument needs a name.")
        tuning = data.get("tuning")
        if not isinstance(tuning, list) or not 1 <= len(tuning) <= 12:
            raise ValueError("Tuning must contain between 1 and 12 strings, bottom to top.")
        for note in tuning:
            if not isinstance(note, str) or not re.fullmatch(r"[A-G](?:#|b)?[0-8]", note):
                raise ValueError("Tuning notes must include octaves, for example E2 or Bb3.")
        fret_count = data.get("fret_count")
        if type(fret_count) is not int or not 1 <= fret_count <= 36:
            raise ValueError("fret_count must be an integer from 1 to 36.")
        for key in ("markers", "double_markers"):
            values = data.get(key, [])
            if not isinstance(values, list) or any(
                type(v) is not int or not 1 <= v <= fret_count for v in values
            ):
                raise ValueError(f"{key} must be a list of positions from 1 to fret_count.")
        if type(data.get("fretted", True)) is not bool:
            raise ValueError("fretted must be true or false.")
        return cls(identifier, name.strip(), tuple(tuning), fret_count,
                   tuple(data.get("markers", [])), tuple(data.get("double_markers", [])),
                   data.get("fretted", True))

    @property
    def string_count(self) -> int:
        return len(self.tuning)

    @property
    def range_label(self) -> str:
        return "Fret range" if self.fretted else "Semitone range"

    def position_label(self, fret: int) -> str:
        if fret == 0:
            return "open string"
        if self.fretted:
            return f"fret {fret}"
        return f"{fret} semitone{'s' if fret != 1 else ''} above open"

    def pitch_at(self, position: Position) -> int:
        if not 1 <= position.string_number <= self.string_count:
            raise ValueError("String number is outside this instrument.")
        if not 0 <= position.fret <= self.fret_count:
            raise ValueError("Fret is outside this instrument.")
        open_note = self.tuning[-position.string_number][:-1]
        return (parse_note(open_note) + position.fret) % 12

    def positions(self, first_fret: int, last_fret: int) -> list[Position]:
        if not 0 <= first_fret <= last_fret <= self.fret_count:
            raise ValueError(f"Select a range within 0–{self.fret_count}, with the start no greater than the end.")
        return [Position(string, fret)
                for string in range(1, self.string_count + 1)
                for fret in range(first_fret, last_fret + 1)]

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "tuning": list(self.tuning),
                "fret_count": self.fret_count, "markers": list(self.markers),
                "double_markers": list(self.double_markers), "fretted": self.fretted}


def load_instruments(custom_directory: Path | None = None) -> tuple[list[Instrument], list[str]]:
    """Load bundled instruments and optional user definitions; reject duplicate IDs."""
    items, warnings = [], []
    sources = sorted(resources.files("tusic").joinpath("instruments").iterdir(), key=lambda p: p.name)
    if custom_directory and custom_directory.is_dir():
        sources.extend(sorted(custom_directory.glob("*.json")))
    seen = set()
    for source in sources:
        if not source.name.endswith(".json"):
            continue
        try:
            instrument = Instrument.from_dict(json.loads(source.read_text(encoding="utf-8")))
            if instrument.id in seen:
                raise ValueError(f"Duplicate instrument id: {instrument.id}")
            seen.add(instrument.id)
            items.append(instrument)
        except (OSError, ValueError) as error:
            warnings.append(f"{source.name}: {error}")
    return items, warnings
