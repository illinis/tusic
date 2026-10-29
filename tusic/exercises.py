"""Question generators and scoring for the seven additional exercise types."""

from dataclasses import dataclass, field
import random

from .music import Instrument, Position
from .practice import Session
from .theory import (BASIC_INTERVALS, INTERVALS, KEYS, SCALES, frequency, midi_name,
                     note_midi, parse_notes, pitch_class, scale_notes, spelled_above, triad)

EXERCISES = {
    "intervals": ("Intervals", "Identify intervals and build notes at a given distance."),
    "scales": ("Build scales", "Write the notes of major, minor, and pentatonic scales."),
    "scale_degrees": ("Scale degrees", "Find a note's degree or name the note at a requested degree."),
    "scale_mapping": ("Scales on the instrument", "Select every scale note within a chosen fretboard region."),
    "diatonic_chords": ("Chords from scales", "Build diatonic triads and identify their quality."),
    "ear_training": ("Ear training", "Hear a tonic and target note, then identify the scale degree."),
    "singing": ("Sing on pitch", "Sing random notes into your microphone and check your tuning."),
}


@dataclass
class Question:
    prompt: str
    kind: str
    expected: object
    explanation: str
    choices: tuple[str, ...] = ()
    context: dict = field(default_factory=dict)
    audio: list = field(default_factory=list)  # (MIDI pitches, duration); empty pitches = rest.

    @property
    def expected_text(self) -> str:
        if self.kind == "positions":
            return f"{len(self.expected)} positions"
        if self.kind == "voice":
            return midi_name(self.expected)
        if self.kind == "chord":
            return f"{' '.join(self.expected[0])} ({self.expected[1]})"
        if self.kind == "notes":
            return " ".join(self.expected)
        return str(self.expected)

    def evaluate(self, value) -> tuple[bool, str]:
        if self.kind == "positions":
            selected = frozenset(value)
            return selected == self.expected, f"{len(selected)} positions selected"
        if self.kind == "chord":
            notes, quality = value
            entered = parse_notes(notes)
            if len(entered) != 3 or quality not in ("major", "minor", "diminished"):
                raise ValueError("Enter three notes in root–third–fifth order and choose a chord quality.")
            return (entered, quality) == self.expected, f"{' '.join(entered)} ({quality})"
        if self.kind == "notes":
            entered = parse_notes(value)
            # An optional repeated tonic is allowed only for a complete scale.
            if self.context.get("complete_scale") and len(entered) == len(self.expected) + 1 and entered[-1] == self.expected[0]:
                entered = entered[:-1]
            if len(entered) != len(self.expected):
                raise ValueError(f"Enter {len(self.expected)} note{'s' if len(self.expected) != 1 else ''} in order.")
            return entered == self.expected, " ".join(entered)
        if self.kind == "choice":
            if value not in self.choices:
                raise ValueError("Choose one of the answers.")
            return value == self.expected, value
        raise ValueError("Voice answers must come from the pitch detector.")


class ExerciseSession(Session):
    def __init__(self, exercise_id: str, question_count: int, options: dict | None = None,
                 instrument: Instrument | None = None, rng: random.Random | None = None):
        super().__init__(question_count)
        if exercise_id not in EXERCISES:
            raise ValueError("Unknown exercise.")
        self.exercise_id, self.instrument = exercise_id, instrument
        self.options = {"key": "Random", "scale": "Major", "mode": "Mixed", "difficulty": "Basic",
                        "first": 0, "last": 5, "low_midi": 48, "high_midi": 72,
                        "tolerance": 35, "hold_seconds": 0.8, "attempt_seconds": 10,
                        **(options or {})}
        if self.options["key"] != "Random" and self.options["key"] not in KEYS:
            raise ValueError("Choose a listed key.")
        if self.options["scale"] not in SCALES:
            raise ValueError("Choose a listed scale.")
        if exercise_id in ("scale_degrees", "diatonic_chords", "ear_training") and self.options["scale"] not in ("Major", "Natural minor"):
            raise ValueError("This exercise uses major or natural minor scales.")
        if self.options["mode"] not in ("Mixed", "Identify", "Build") or self.options["difficulty"] not in ("Basic", "All"):
            raise ValueError("Choose a listed mode and difficulty.")
        if exercise_id == "scale_mapping":
            if instrument is None:
                raise ValueError("Select an instrument.")
            instrument.positions(self.options["first"], self.options["last"])
        if exercise_id == "singing":
            if not 36 <= self.options["low_midi"] <= self.options["high_midi"] <= 84:
                raise ValueError("Choose an ascending vocal range between C2 and C6.")
            if not 10 <= self.options["tolerance"] <= 50 or not 0.4 <= self.options["hold_seconds"] <= 3:
                raise ValueError("Use a tolerance of 10–50 cents and hold time of 0.4–3 seconds.")
        rng = rng or random.Random()
        vocal_pool = []
        for _ in range(question_count):
            if exercise_id == "singing":
                if not vocal_pool:
                    vocal_pool = list(range(self.options["low_midi"], self.options["high_midi"] + 1))
                    rng.shuffle(vocal_pool)
                    if len(vocal_pool) > 1 and self.questions and vocal_pool[-1] == self.questions[-1].expected:
                        vocal_pool[-1], vocal_pool[0] = vocal_pool[0], vocal_pool[-1]
                midi = vocal_pool.pop()
                self.questions.append(Question(f"Sing {midi_name(midi)}", "voice", midi,
                    f"Target: {midi_name(midi)} ({frequency(midi):.1f} Hz). Match the displayed octave.",
                    context={"target_midi": midi, "target_hz": frequency(midi)}, audio=[([midi], 1.0)]))
            else:
                self.questions.append(self.generate(rng))

    @property
    def title(self) -> str:
        return EXERCISES[self.exercise_id][0]

    def generate(self, rng: random.Random) -> Question:
        root = rng.choice(KEYS) if self.options["key"] == "Random" else self.options["key"]
        kind = self.options["scale"]
        scale = scale_notes(root, kind)
        context = {"tonic": root, "scale": kind, "scale_notes": list(scale)}
        scale_text = f"{root} {kind.lower()}"
        explanation = f"{scale_text}: {' – '.join(scale)}."
        mode = rng.choice(("Identify", "Build")) if self.options["mode"] == "Mixed" else self.options["mode"]
        if self.exercise_id == "intervals":
            choices = BASIC_INTERVALS if self.options["difficulty"] == "Basic" else tuple(INTERVALS)
            name = rng.choice(choices)
            letters, semitones = INTERVALS[name]
            target = spelled_above(root, letters, semitones)
            target_octave = 4 + ("CDEFGAB".index(root[0]) + letters) // 7
            explanation = f"{root} → {target}: {name.lower()}, {semitones} semitones. Letter spelling matters."
            context = {"root": root, "target": target, "interval": name, "semitones": semitones}
            audio = [([note_midi(root)], 0.6), ([], 0.15), ([note_midi(root) + semitones], 0.7)]
            if mode == "Identify":
                return Question(f"Name the ascending interval: {root}4 → {target}{target_octave}", "choice", name,
                                explanation, tuple(choices), context, audio)
            return Question(f"Write the note a {name.lower()} above {root}.", "notes", (target,), explanation,
                            context=context, audio=audio)
        if self.exercise_id == "scales":
            return Question(f"Write {scale_text}, starting on {root} and ascending.", "notes", scale, explanation,
                            context={**context, "complete_scale": True})
        if self.exercise_id == "scale_degrees":
            degree = rng.randrange(7)
            context["degree"] = degree + 1
            if mode == "Identify":
                return Question(f"In {scale_text}, what scale degree is {scale[degree]}?", "choice", str(degree + 1),
                                explanation, tuple(str(i) for i in range(1, 8)), context)
            return Question(f"What note is degree {degree + 1} of {scale_text}?", "notes", (scale[degree],), explanation, context=context)
        if self.exercise_id == "scale_mapping":
            pitches = {pitch_class(note) for note in scale}
            expected = frozenset(position for position in self.instrument.positions(self.options["first"], self.options["last"])
                                 if self.instrument.pitch_at(position) in pitches)
            return Question(f"Select EVERY {scale_text} note in the highlighted region.", "positions", expected,
                            explanation, context=context)
        if self.exercise_id == "diatonic_chords":
            degree = rng.randint(1, 7)
            notes, quality, roman = triad(root, kind, degree)
            return Question(f"Build the triad on degree {degree} of {scale_text}.", "chord", (notes, quality),
                            f"{roman}: {' – '.join(notes)}, {quality}. Stack alternate scale notes (root, third, fifth). {explanation}",
                            context={**context, "degree": degree, "roman": roman})
        degree = rng.randrange(7)
        tonic = note_midi(root)
        offsets = SCALES[kind][0]
        audio = [([tonic, tonic + offsets[2], tonic + offsets[4]], 0.8), ([], 0.25),
                 ([tonic], 0.6), ([], 0.3), ([tonic + offsets[degree]], 0.8)]
        return Question(f"Listen in {scale_text}. What degree is the final note?", "choice", str(degree + 1),
                        f"The final note is {scale[degree]}, degree {degree + 1}. {explanation}",
                        tuple(str(i) for i in range(1, 8)), {**context, "degree": degree + 1}, audio)

    def submit(self, value) -> dict:
        correct, display = self.current.evaluate(value)
        details = {}
        if self.current.kind == "positions":
            encode = lambda items: [{"string_number": p.string_number, "fret": p.fret}
                                    for p in sorted(items, key=lambda p: (p.string_number, p.fret))]
            details = {"selected_positions": encode(value), "expected_positions": encode(self.current.expected)}
        return self.record_result(correct, display, details)

    def record_result(self, correct: bool, display: str, details: dict | None = None) -> dict:
        return self.record_answer({"prompt": self.current.prompt, "answer": display,
                                  "expected_answer": self.current.expected_text, "correct": bool(correct),
                                  "context": self.current.context, **(details or {})})

    def to_dict(self) -> dict:
        result = {**super().to_dict(), "exercise_id": self.exercise_id, "options": dict(self.options)}
        if self.instrument:
            result["instrument"] = self.instrument.to_dict()
        return result
