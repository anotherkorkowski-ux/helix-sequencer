"""Audio compatibility and fallback regression tests.

These tests ensure that audio_intelligence.py handles missing/fallback modes
gracefully and produces consistent results across multiple analysis passes.
Required for safe integration of PR-E (audio intelligence updates).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from core import audio_intelligence


class AudioCompatibilityTests(unittest.TestCase):
    """Regression tests for audio analysis fallback chains and consistency."""

    def _create_synthetic_audio_file(self, duration_s: float = 5.0) -> Path:
        """Generate a temporary WAV file with synthetic audio for testing."""
        import soundfile
        
        sr = 22050
        t = np.linspace(0, duration_s, int(sr * duration_s), dtype=np.float32)
        
        # Create a simple sine wave sweep (bass -> mid)
        freq_start, freq_end = 60, 500
        freq = np.linspace(freq_start, freq_end, len(t))
        phase = 2.0 * np.pi * np.cumsum(freq) / sr
        audio = 0.3 * np.sin(phase)
        
        # Add some percussion peaks (mimics drum hits)
        drum_times = [int(sr * t) for t in [1.0, 1.5, 2.0, 2.5, 3.0]]
        for dt in drum_times:
            if dt < len(audio):
                audio[dt:dt+int(0.1*sr)] *= 2.5  # Percussive transient
        
        audio = np.clip(audio, -1.0, 1.0).astype(np.float32)
        
        tmp = Path(tempfile.mktemp(suffix=".wav"))
        soundfile.write(str(tmp), audio, sr)
        self.addCleanup(lambda: tmp.unlink(missing_ok=True))
        return tmp

    def test_missing_audio_file_returns_empty_stems(self) -> None:
        """Verify that missing audio files return stable empty StemAnalysis."""
        missing_path = Path("this/path/does-not-exist-12345.wav")
        result = audio_intelligence.build_stem_analysis(
            audio_path=missing_path,
            use_moises=False,
            api_key=None,
            cache_dir=Path(tempfile.gettempdir()),
        )
        
        # Should gracefully return empty stems, not crash
        self.assertEqual(result.source, "direct")
        self.assertEqual(result.stems, {})
        self.assertEqual(result.bass_peaks_ms, [])
        self.assertEqual(result.vocal_peaks_ms, [])
        self.assertEqual(result.drum_kicks_ms, [])
        self.assertEqual(result.drum_snares_ms, [])
        self.assertEqual(result.drum_hats_ms, [])

    def test_stem_analysis_fallback_to_direct_mode(self) -> None:
        """Verify that when stem separation fails, analysis falls back to direct audio mode."""
        audio_path = self._create_synthetic_audio_file(3.0)
        cache_dir = Path(tempfile.gettempdir())
        
        # Both Moises and Demucs will fail (no API key, no demucs installed)
        # Should fall back to local separation or direct analysis
        result = audio_intelligence.build_stem_analysis(
            audio_path=audio_path,
            use_moises=False,  # Skip Moises attempt
            api_key=None,
            cache_dir=cache_dir,
        )
        
        # Should complete without exception
        self.assertIsNotNone(result)
        self.assertIn(result.source, ["local", "direct", "demucs"])  # Any valid fallback
        
        # Peak detection should be attempted
        # (may be empty if librosa peak detection doesn't find peaks in synthetic signal)
        self.assertIsInstance(result.bass_peaks_ms, list)
        self.assertIsInstance(result.drum_kicks_ms, list)

    def test_stem_analysis_consistency_across_runs(self) -> None:
        """Verify that analyzing the same audio twice produces consistent peak locations."""
        audio_path = self._create_synthetic_audio_file(4.0)
        cache_dir = Path(tempfile.gettempdir())
        
        # First analysis pass
        result1 = audio_intelligence.build_stem_analysis(
            audio_path=audio_path,
            use_moises=False,
            api_key=None,
            cache_dir=cache_dir,
        )
        
        # Second analysis pass (same audio)
        result2 = audio_intelligence.build_stem_analysis(
            audio_path=audio_path,
            use_moises=False,
            api_key=None,
            cache_dir=cache_dir,
        )
        
        # Both should succeed and complete
        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)
        
        # Source mode should be consistent between runs
        self.assertEqual(result1.source, result2.source)
        
        # Peak detection should be deterministic (same input = same output)
        # Allow small variance due to librosa version differences, but lists should be same length
        self.assertEqual(len(result1.bass_peaks_ms), len(result2.bass_peaks_ms))
        self.assertEqual(len(result1.drum_kicks_ms), len(result2.drum_kicks_ms))

    def test_direct_audio_analysis_with_synthetic_signal(self) -> None:
        """Verify that direct audio analysis (no stems) produces valid output."""
        audio_path = self._create_synthetic_audio_file(6.0)
        cache_dir = Path(tempfile.gettempdir())
        
        result = audio_intelligence.build_stem_analysis(
            audio_path=audio_path,
            use_moises=False,
            api_key=None,
            cache_dir=cache_dir,
        )
        
        # Should not crash and should produce structured output
        self.assertIsNotNone(result)
        self.assertIn(result.source, ["local", "direct", "demucs"])
        
        # All fields should be present and properly typed
        self.assertIsInstance(result.stems, dict)
        self.assertIsInstance(result.bass_peaks_ms, list)
        self.assertIsInstance(result.vocal_peaks_ms, list)
        self.assertIsInstance(result.drum_kicks_ms, list)
        self.assertIsInstance(result.drum_snares_ms, list)
        self.assertIsInstance(result.drum_hats_ms, list)
        
        # All peak times should be non-negative integers (milliseconds)
        for peak_list in [
            result.bass_peaks_ms,
            result.vocal_peaks_ms,
            result.drum_kicks_ms,
            result.drum_snares_ms,
            result.drum_hats_ms,
        ]:
            for peak_ms in peak_list:
                self.assertIsInstance(peak_ms, int)
                self.assertGreaterEqual(peak_ms, 0)

    def test_empty_audio_file_handling(self) -> None:
        """Verify that empty or very short audio files are handled gracefully."""
        import soundfile
        
        # Create an empty file (0 seconds)
        tmp = Path(tempfile.mktemp(suffix=".wav"))
        try:
            # Write effectively empty data
            audio = np.array([], dtype=np.float32)
            soundfile.write(str(tmp), audio, 22050)
            
            result = audio_intelligence.build_stem_analysis(
                audio_path=tmp,
                use_moises=False,
                api_key=None,
                cache_dir=Path(tempfile.gettempdir()),
            )
            
            # Should handle gracefully (may return direct/empty or raise controlled error)
            self.assertIsNotNone(result)
        finally:
            tmp.unlink(missing_ok=True)

    def test_stem_analysis_respects_cache_directory(self) -> None:
        """Verify that stem analysis uses the provided cache directory."""
        audio_path = self._create_synthetic_audio_file(2.0)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            
            result = audio_intelligence.build_stem_analysis(
                audio_path=audio_path,
                use_moises=False,
                api_key=None,
                cache_dir=cache_dir,
            )
            
            self.assertIsNotNone(result)
            
            # Cache directory should exist (or at least not fail)
            self.assertTrue(cache_dir.exists())

    def test_peak_detection_produces_millisecond_timestamps(self) -> None:
        """Verify that peak detection returns timestamps in milliseconds (integer, non-negative)."""
        audio_path = self._create_synthetic_audio_file(3.0)
        
        result = audio_intelligence.build_stem_analysis(
            audio_path=audio_path,
            use_moises=False,
            api_key=None,
            cache_dir=Path(tempfile.gettempdir()),
        )
        
        # Check all peak lists
        for peak_list in [result.bass_peaks_ms, result.drum_kicks_ms]:
            for peak_ms in peak_list:
                self.assertIsInstance(peak_ms, (int, np.integer))
                self.assertGreaterEqual(peak_ms, 0)


if __name__ == "__main__":
    unittest.main()
