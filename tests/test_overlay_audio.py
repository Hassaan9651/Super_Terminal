import io
import unittest
import wave

from utils.overlay import frames_to_wav_bytes, SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH


class TestFramesToWavBytes(unittest.TestCase):

    def test_produces_valid_wav_with_expected_format(self):
        frames = b"\x00\x01" * 1600  # 0.1s of 16 kHz int16 mono audio
        wav_bytes = frames_to_wav_bytes(frames)

        with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
            self.assertEqual(wav_file.getnchannels(), CHANNELS)
            self.assertEqual(wav_file.getsampwidth(), SAMPLE_WIDTH)
            self.assertEqual(wav_file.getframerate(), SAMPLE_RATE)
            self.assertEqual(wav_file.readframes(wav_file.getnframes()), frames)

    def test_empty_frames_still_produce_valid_wav_header(self):
        wav_bytes = frames_to_wav_bytes(b"")

        with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
            self.assertEqual(wav_file.getnframes(), 0)


if __name__ == "__main__":
    unittest.main()
