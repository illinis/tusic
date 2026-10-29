"""Local monophonic pitch detection and sustained-pitch grading.

Uses YIN's cumulative-mean normalized difference function, with FFT correlation
to calculate fixed-window differences. No trained model or downloaded assets.
"""

from dataclasses import dataclass
import math

import numpy as np

from .theory import frequency, midi_name


@dataclass(frozen=True)
class PitchReading:
    hz: float | None
    confidence: float
    rms: float
    reason: str = ""


def detect_pitch(samples, sample_rate: float, fmin: float = 60, fmax: float = 1200) -> PitchReading:
    x = np.asarray(samples, dtype=np.float64).reshape(-1)
    if not len(x) or sample_rate <= 0 or not np.isfinite(x).all():
        return PitchReading(None, 0, 0, "Waiting for audio")
    x = x - x.mean()
    rms = float(np.sqrt(np.mean(x * x)))
    if rms < 0.005:
        return PitchReading(None, 0, rms, "Too quiet — sing closer to the microphone")
    if np.mean(np.abs(x) >= 0.98) > 0.03:
        return PitchReading(None, 0, rms, "Audio is clipping — reduce microphone gain")
    lo = max(2, int(sample_rate / fmax))
    hi = min(int(math.ceil(sample_rate / fmin)), len(x) // 2 - 1)
    if hi <= lo + 2:
        return PitchReading(None, 0, rms, "Waiting for more audio")
    window = len(x) - hi
    nfft = 1 << (len(x) + window - 1).bit_length()
    correlation = np.fft.irfft(np.conj(np.fft.rfft(x[:window], nfft)) * np.fft.rfft(x, nfft), nfft)[:hi + 1]
    energy = np.concatenate(([0.0], np.cumsum(x * x)))
    lags = np.arange(hi + 1)
    difference = np.maximum(energy[window] + energy[lags + window] - energy[lags] - 2 * correlation, 0)
    normalized = np.ones(hi + 1)
    normalized[1:] = difference[1:] * np.arange(1, hi + 1) / np.maximum(np.cumsum(difference[1:]), 1e-12)
    candidates = np.flatnonzero(normalized[lo:hi] < 0.12)
    if not len(candidates):
        return PitchReading(None, 0, rms, "No steady pitch — sing one sustained note")
    lag = int(candidates[0] + lo)
    while lag + 1 < hi and normalized[lag + 1] < normalized[lag]:
        lag += 1
    confidence = float(1 - normalized[lag])
    previous, current, following = normalized[lag - 1:lag + 2]
    denominator = previous - 2 * current + following
    adjustment = 0.5 * (previous - following) / denominator if abs(denominator) > 1e-12 else 0
    refined = lag + float(np.clip(adjustment, -1, 1))
    hz = float(sample_rate / refined)
    if not fmin <= hz <= fmax or confidence < 0.85:
        return PitchReading(None, confidence, rms, "No reliable vocal pitch")
    return PitchReading(hz, confidence, rms)


def cents_from_target(hz: float, target_midi: int) -> float:
    return 1200 * math.log2(hz / frequency(target_midi))


def heard_note(hz: float) -> str:
    midi = round(69 + 12 * math.log2(hz / 440))
    return midi_name(midi)


class PitchHold:
    """Only fresh, consecutive voiced frames can complete a target."""

    def __init__(self, target_midi: int, tolerance: float = 35, hold_seconds: float = 0.8):
        self.target_midi, self.tolerance, self.required = target_midi, tolerance, hold_seconds
        self.held = 0.0
        self.best_cents: float | None = None
        self.last_cents: float | None = None
        self.last_hz: float | None = None

    def update(self, reading: PitchReading, seconds: float) -> bool:
        if reading.hz is None or reading.confidence < 0.85 or seconds <= 0 or seconds > 0.25:
            self.held = 0
            self.last_cents = None
            return False
        self.last_hz = reading.hz
        self.last_cents = cents_from_target(reading.hz, self.target_midi)
        if self.best_cents is None or abs(self.last_cents) < abs(self.best_cents):
            self.best_cents = self.last_cents
        if abs(self.last_cents) <= self.tolerance:
            self.held += min(seconds, 0.10)
        else:
            self.held = 0
        return self.held + 1e-9 >= self.required

    def summary(self) -> dict:
        return {"target_midi": self.target_midi, "target_hz": round(frequency(self.target_midi), 3),
                "tolerance_cents": self.tolerance, "required_hold_seconds": self.required,
                "held_seconds": round(self.held, 3),
                "last_detected_hz": round(self.last_hz, 3) if self.last_hz is not None else None,
                "best_cents_error": round(self.best_cents, 2) if self.best_cents is not None else None}
