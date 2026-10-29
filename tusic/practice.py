"""Quiz state, randomization, and an analytics-friendly session record."""

from datetime import datetime, timezone
import random
import time
from uuid import uuid4

from .music import Instrument, Position, SHARPS, FLATS, parse_note


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Session:
    """Shared scoring and lifecycle for every locally saved exercise."""

    def __init__(self, question_count: int):
        if type(question_count) is not int or not 1 <= question_count <= 500:
            raise ValueError("Choose between 1 and 500 questions.")
        self.question_count = question_count
        self.questions = []
        self.id = uuid4().hex
        self.started_at = utc_now()
        self.ended_at: str | None = None
        self.status = "in_progress"
        self.answers: list[dict] = []
        self.index = 0
        self._started_clock = time.monotonic()
        self._question_clock = time.monotonic()
        self._ended_clock: float | None = None

    @property
    def current(self):
        return self.questions[self.index]

    @property
    def answered_current(self) -> bool:
        return len(self.answers) > self.index

    @property
    def correct_count(self) -> int:
        return sum(answer["correct"] for answer in self.answers)

    @property
    def accuracy(self) -> float:
        return round(100 * self.correct_count / len(self.answers), 1) if self.answers else 0.0

    def record_answer(self, answer: dict) -> dict:
        if self.status != "in_progress" or self.answered_current:
            raise ValueError("This question has already been answered.")
        answer = {**answer,
            "question_number": self.index + 1,
            "response_seconds": round(time.monotonic() - self._question_clock, 3),
            "answered_at": utc_now(),
        }
        self.answers.append(answer)
        if len(self.answers) == self.question_count:
            self.finish("completed")
        return answer

    def advance(self) -> bool:
        if not self.answered_current:
            raise ValueError("Answer the current question first.")
        if self.status != "in_progress":
            return False
        self.index += 1
        self._question_clock = time.monotonic()
        return True

    def finish(self, status: str = "abandoned") -> None:
        if status not in ("completed", "abandoned"):
            raise ValueError("Unknown end status.")
        if status == "completed" and len(self.answers) != self.question_count:
            raise ValueError("An incomplete match cannot be marked completed.")
        if self.status == "in_progress":
            self.status = status
            self.ended_at = utc_now()
            self._ended_clock = time.monotonic()

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "id": self.id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "requested_questions": self.question_count,
            "total_answered": len(self.answers),
            "correct_count": self.correct_count,
            "accuracy_percent": self.accuracy,
            "duration_seconds": round((self._ended_clock or time.monotonic()) - self._started_clock, 3),
            "answers": [dict(answer) for answer in self.answers],
        }


class PracticeSession(Session):
    def __init__(self, instrument: Instrument, question_count: int,
                 first_fret: int = 0, last_fret: int | None = None,
                 rng: random.Random | None = None):
        super().__init__(question_count)
        self.instrument = instrument
        self.first_fret = first_fret
        self.last_fret = instrument.fret_count if last_fret is None else last_fret
        pool = instrument.positions(self.first_fret, self.last_fret)
        rng = rng or random.Random()
        while len(self.questions) < question_count:
            batch = pool.copy()
            rng.shuffle(batch)
            if len(batch) > 1 and self.questions and batch[0] == self.questions[-1]:
                batch[0], batch[1] = batch[1], batch[0]
            self.questions.extend(batch[:question_count - len(self.questions)])

    def submit(self, text: str) -> dict:
        pitch = parse_note(text)
        target = self.instrument.pitch_at(self.current)
        return self.record_answer({
            "string_number": self.current.string_number,
            "fret": self.current.fret,
            "expected_pitch_class": target,
            "expected_notes": list(dict.fromkeys((SHARPS[target], FLATS[target]))),
            "answer": text.strip(),
            "answer_pitch_class": pitch,
            "correct": pitch == target,
        })

    def to_dict(self) -> dict:
        return {**super().to_dict(), "exercise_id": "fretboard_notes",
                "instrument": self.instrument.to_dict(),
                "fret_range": {"first": self.first_fret, "last": self.last_fret}}
