"""Offline tone synthesis, playback and bounded in-memory microphone capture."""

import queue
import time

import numpy as np

from .theory import frequency


def synthesize(events, sample_rate=44100, volume=0.18):
    parts = []
    for pitches, seconds in events:
        count = max(1, int(seconds * sample_rate))
        tone = np.zeros(count, dtype=np.float64)
        t = np.arange(count) / sample_rate
        for midi in pitches:
            hz = frequency(midi)
            tone += np.sin(2 * np.pi * hz * t) + 0.15 * np.sin(4 * np.pi * hz * t)
        if pitches:
            tone *= volume / (1.15 * len(pitches))
            ramp = min(int(0.02 * sample_rate), count // 2)
            if ramp:
                tone[:ramp] *= np.linspace(0, 1, ramp)
                tone[-ramp:] *= np.linspace(1, 0, ramp)
        parts.append(tone.astype(np.float32))
    return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)


class AudioBackend:
    def __init__(self):
        try:
            import sounddevice as sd
        except (ImportError, OSError) as error:
            raise RuntimeError("Audio support is unavailable. Install requirements.txt; on Linux also install libportaudio2.") from error
        self.sd = sd
        self.playing = False

    def devices(self, kind: str):
        apis = self.sd.query_hostapis()
        return [(index, f"{device['name']} [{apis[device['hostapi']]['name']}]")
                for index, device in enumerate(self.sd.query_devices()) if device[f"max_{kind}_channels"] > 0]

    def play(self, events, device=None, volume=0.18) -> float:
        self.stop()
        info = self.sd.query_devices(device, "output")
        rate = int(info["default_samplerate"])
        samples = synthesize(events, rate, volume)
        self.sd.play(samples, rate, device=device, blocking=False)
        self.playing = True
        return len(samples) / rate

    def stop(self):
        if self.playing:
            self.sd.stop()
            self.playing = False

    def microphone(self, device=None):
        return Microphone(self.sd, device)


class Microphone:
    def __init__(self, sd, device=None):
        self.blocks = queue.Queue(maxsize=8)
        self.buffer = np.zeros(0, dtype=np.float32)
        self.sample_rate = int(sd.query_devices(device, "input")["default_samplerate"])
        self.window_size = max(2048, int(self.sample_rate * 0.14))
        self.stream = None

        def callback(data, frames, clock, status):
            overrun = bool(status)
            if self.blocks.full():
                try:
                    self.blocks.get_nowait()
                    overrun = True
                except queue.Empty:
                    pass
            self.blocks.put_nowait((data[:, 0].copy(), time.monotonic(), overrun))

        try:
            self.stream = sd.InputStream(device=device, channels=1, samplerate=self.sample_rate,
                                         blocksize=max(512, int(self.sample_rate * 0.05)), dtype="float32",
                                         callback=callback)
            self.stream.start()
        except Exception:
            self.close()
            raise

    def read(self):
        blocks, captured, overrun = [], None, False
        while True:
            try:
                data, captured, bad = self.blocks.get_nowait()
                blocks.append(data)
                overrun |= bad
            except queue.Empty:
                break
        if not blocks:
            return None
        data = np.concatenate(blocks)
        self.buffer = np.concatenate((self.buffer, data))[-self.window_size:]
        stale = captured is None or time.monotonic() - captured > 0.25
        if overrun or stale:
            self.buffer = np.zeros(0, dtype=np.float32)
            return None, self.sample_rate, 0, "Audio interrupted; listening again"
        if len(self.buffer) < self.window_size:
            return None
        return self.buffer, self.sample_rate, min(len(data) / self.sample_rate, 0.10), ""

    @property
    def active(self):
        return self.stream is not None and self.stream.active

    def close(self):
        if self.stream is not None:
            try:
                self.stream.abort()
            finally:
                self.stream.close()
                self.stream = None
        self.buffer = np.zeros(0, dtype=np.float32)
        while not self.blocks.empty():
            try:
                self.blocks.get_nowait()
            except queue.Empty:
                break
