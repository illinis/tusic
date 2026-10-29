import unittest
from unittest.mock import Mock

import numpy as np

from tusic.audio import AudioBackend, Microphone, synthesize
from tusic.pitch import PitchHold, PitchReading, cents_from_target, detect_pitch
from tusic.theory import frequency


class PitchTests(unittest.TestCase):
    def signal(self, hz, rate=48000, seconds=0.14):
        t = np.arange(int(rate * seconds)) / rate
        return 0.3 * np.sin(2 * np.pi * hz * t)

    def test_pitch_accuracy_across_vocal_range_and_sample_rates(self):
        for rate in (44100, 48000):
            for midi in range(36, 85):
                with self.subTest(rate=rate, midi=midi):
                    reading = detect_pitch(self.signal(frequency(midi), rate), rate)
                    self.assertIsNotNone(reading.hz)
                    self.assertLess(abs(cents_from_target(reading.hz, midi)), 3)

    def test_harmonics_noise_and_detuning(self):
        rng = np.random.default_rng(7)
        t = np.arange(6720) / 48000
        hz = frequency(57) * 2 ** (27 / 1200)
        signal = 0.2 * np.sin(2*np.pi*hz*t) + 0.35 * np.sin(4*np.pi*hz*t) + 0.08 * np.sin(6*np.pi*hz*t)
        signal += rng.normal(0, 0.008, len(t))
        reading = detect_pitch(signal, 48000)
        self.assertIsNotNone(reading.hz)
        self.assertAlmostEqual(cents_from_target(reading.hz, 57), 27, delta=3)

    def test_silence_noise_clipping_and_invalid_audio_rejected(self):
        for data in (np.zeros(6720), np.random.default_rng(9).normal(0, 0.1, 6720),
                     np.array([np.nan]*6720), np.sign(self.signal(220))):
            with self.subTest(kind=str(data[:3])):
                self.assertIsNone(detect_pitch(data, 48000).hz)

    def test_sustained_pitch_not_octave_or_noise(self):
        hold = PitchHold(69, 35, 0.8)
        for _ in range(15):
            self.assertFalse(hold.update(PitchReading(880, 0.99, 0.2), 0.1))
        for _ in range(7):
            self.assertFalse(hold.update(PitchReading(440, 0.99, 0.2), 0.1))
        hold.update(PitchReading(None, 0, 0), 0.1)
        self.assertEqual(hold.held, 0)
        for _ in range(7):
            self.assertFalse(hold.update(PitchReading(442, 0.99, 0.2), 0.1))
        self.assertTrue(hold.update(PitchReading(442, 0.99, 0.2), 0.1))
        self.assertIn("best_cents_error", hold.summary())

    def test_stale_frame_cannot_complete_hold(self):
        hold = PitchHold(69)
        self.assertFalse(hold.update(PitchReading(440, 0.99, 0.2), 5))
        self.assertEqual(hold.held, 0)


class AudioTests(unittest.TestCase):
    def test_generated_tones_have_envelope_silence_and_bounded_volume(self):
        data = synthesize([([69], 0.5), ([], 0.2), ([60, 64, 67], 0.5)], 44100)
        self.assertEqual(len(data), int(44100*1.2))
        self.assertLessEqual(np.max(np.abs(data)), 0.181)
        self.assertEqual(float(data[0]), 0)
        self.assertEqual(float(data[-1]), 0)
        self.assertTrue(np.all(data[22050:30870] == 0))
        reading = detect_pitch(data[4000:10000], 44100)
        self.assertAlmostEqual(reading.hz, 440, delta=1)

    def test_device_filtering_and_lazy_streams(self):
        backend = AudioBackend.__new__(AudioBackend)
        backend.sd = Mock()
        backend.sd.query_hostapis.return_value = [{"name": "test"}]
        backend.sd.query_devices.return_value = [
            {"name": "mic", "hostapi": 0, "max_input_channels": 1, "max_output_channels": 0},
            {"name": "speaker", "hostapi": 0, "max_input_channels": 0, "max_output_channels": 2}]
        self.assertEqual(backend.devices("input"), [(0, "mic [test]")])
        self.assertEqual(backend.devices("output"), [(1, "speaker [test]")])
        backend.sd.InputStream.assert_not_called()

    def test_microphone_closes_on_start_failure(self):
        sd = Mock()
        sd.query_devices.return_value = {"default_samplerate": 48000}
        sd.InputStream.return_value.start.side_effect = RuntimeError("permission denied")
        with self.assertRaises(RuntimeError):
            Microphone(sd)
        sd.InputStream.return_value.close.assert_called_once()

    def test_capture_is_in_memory_and_discards_overruns(self):
        sd = Mock()
        sd.query_devices.return_value = {"default_samplerate": 48000}
        microphone = Microphone(sd)
        callback = sd.InputStream.call_args.kwargs["callback"]
        for _ in range(3):
            callback(np.ones((2400, 1), dtype=np.float32), 2400, None, False)
        block = microphone.read()
        self.assertEqual(len(block[0]), microphone.window_size)
        self.assertLessEqual(block[2], 0.1)
        self.assertIsNone(microphone.read())  # Never reuse a frame as a fresh observation.
        callback(np.ones((2400, 1), dtype=np.float32), 2400, None, True)
        self.assertIsNone(microphone.read()[0])
        microphone.close()
        self.assertEqual(len(microphone.buffer), 0)
        self.assertTrue(microphone.blocks.empty())


if __name__ == "__main__":
    unittest.main()
