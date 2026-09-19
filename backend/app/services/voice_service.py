"""
Voice Service for SMART AI IoT.

Provides Speech-to-Text (STT) and Text-to-Speech (TTS) optimized for
Indonesian language (Bahasa Indonesia), supporting various intonations,
accents, background noise calibration, and speech synthesis.
"""

from __future__ import annotations

import base64
import io
import math
import time
from typing import Any, Callable, Optional

try:
    import numpy as np
except ImportError:
    np = None

try:
    import sounddevice as sd
except Exception:
    sd = None

try:
    import soundfile as sf
except Exception:
    sf = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("voice_service")


class VoiceService:
    """
    Comprehensive voice service supporting:
    - Indonesian Speech-to-Text (STT) with Google Web Speech API + Gemini Multimodal fallback
    - Text-to-Speech (TTS) with natural Indonesian voice (gTTS)
    - Microphone recording with Voice Activity Detection (VAD) and noise floor calibration
    - Audio format conversion and streaming
    """

    def __init__(self) -> None:
        if sr is not None:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 1.0
        else:
            self.recognizer = None
        self.default_sample_rate = 16000
        self.default_language = "id-ID"

    # ── Speech to Text (STT) ─────────────────────────────────

    def transcribe_audio_bytes(
        self,
        audio_bytes: bytes,
        language: str = "id-ID",
    ) -> str:
        """
        Transcribe raw audio bytes (WAV, MP3, OGG, FLAC, etc.) to text.

        Uses Google Speech Recognition (id-ID) as primary engine, with
        automatic Gemini Multimodal Audio fallback if network or recognition issues occur.
        """
        if not audio_bytes or len(audio_bytes) < 100:
            return ""

        audio_data = None
        # Step 1: Decode audio bytes to numpy array using soundfile
        if sf is not None and np is not None and sr is not None:
            try:
                audio_io = io.BytesIO(audio_bytes)
                data, samplerate = sf.read(audio_io, dtype="int16")
                if len(data.shape) > 1:
                    data = data.mean(axis=1).astype(np.int16)

                audio_data = sr.AudioData(data.tobytes(), samplerate, 2)
            except Exception as e:
                logger.warning("soundfile_decode_error", error=str(e))

        if audio_data is None and sr is not None:
            try:
                audio_data = sr.AudioData(audio_bytes, self.default_sample_rate, 2)
            except Exception:
                pass

        # Step 2: Primary STT via Google Speech Recognition
        if audio_data is not None and self.recognizer is not None and sr is not None:
            try:
                transcript = self.recognizer.recognize_google(
                    audio_data,
                    language=language,
                    show_all=False,
                )
                if transcript and isinstance(transcript, str):
                    logger.info("google_stt_success", transcript=transcript)
                    return transcript.strip()
            except sr.UnknownValueError:
                logger.info("google_stt_unrecognized_speech")
                return ""
            except (sr.RequestError, Exception) as exc:
                logger.warning("google_stt_failed_trying_gemini", error=str(exc))

        # Step 3: Fallback STT via Google Gemini Multimodal
        try:
            gemini_transcript = self._transcribe_with_gemini(audio_bytes)
            if gemini_transcript:
                logger.info("gemini_stt_success", transcript=gemini_transcript)
                return gemini_transcript.strip()
        except Exception as gemini_err:
            logger.warning("gemini_stt_fallback_failed", error=str(gemini_err))

        return ""

    def _transcribe_with_gemini(self, audio_bytes: bytes) -> str:
        """Fallback STT using Gemini Multimodal Audio understanding."""
        import google.generativeai as genai
        if not settings.GEMINI_API_KEY:
            return ""

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        audio_part = {
            "mime_type": "audio/wav",
            "data": audio_bytes,
        }
        prompt = (
            "Transkripsikan isi rekaman suara bahasa Indonesia ini secara presisi dan tepat. "
            "Keluarkan HANYA teks transkripsi dari apa yang diucapkan pengguna, tanpa tambahan teks atau tanda petik."
        )
        response = model.generate_content([prompt, audio_part])
        if response and response.text:
            return response.text.strip()
        return ""

    # ── Text to Speech (TTS) ─────────────────────────────────

    def synthesize_speech(
        self,
        text: str,
        language: str = "id",
        slow: bool = False,
    ) -> bytes:
        """
        Synthesize Indonesian text to natural-sounding MP3 audio bytes.
        """
        if not text or not text.strip() or gTTS is None:
            return b""

        clean_text = text.strip()
        clean_text = clean_text.replace("**", "").replace("*", "").replace("#", "")

        try:
            tts = gTTS(text=clean_text, lang=language, tld="co.id", slow=slow)
            mp3_fp = io.BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            return mp3_fp.getvalue()
        except Exception as e:
            logger.error("tts_synthesis_error", error=str(e), text=text)
            return b""

    def play_audio_bytes(
        self,
        audio_bytes: bytes,
        blocking: bool = True,
    ) -> bool:
        """
        Play audio bytes (MP3 or WAV) through the default system output speaker.
        """
        if not audio_bytes or sf is None or sd is None:
            return False

        try:
            audio_io = io.BytesIO(audio_bytes)
            data, samplerate = sf.read(audio_io, dtype="float32")
            sd.play(data, samplerate)
            if blocking:
                sd.wait()
            return True
        except Exception as e:
            logger.warning("audio_playback_error", error=str(e))
            return False

    def speak(self, text: str, blocking: bool = True) -> bytes:
        """
        Convenience method to synthesize text and immediately play it.
        Returns the generated MP3 bytes.
        """
        audio_bytes = self.synthesize_speech(text)
        if audio_bytes:
            self.play_audio_bytes(audio_bytes, blocking=blocking)
        return audio_bytes

    # ── Microphone Recording with VAD ─────────────────────────

    def record_microphone(
        self,
        max_duration: float = 12.0,
        silence_limit: float = 1.3,
        sample_rate: int = 16000,
        status_callback: Optional[Callable[[str, Any], None]] = None,
        stop_event: Optional[Any] = None,
    ) -> bytes | None:
        """
        Record audio from the default microphone using dynamic Voice Activity Detection (VAD).
        """
        if sd is None or np is None or sf is None:
            logger.warning("microphone_libraries_not_installed")
            return None

        chunk_duration = 0.08
        chunk_samples = int(sample_rate * chunk_duration)
        channels = 1

        if status_callback:
            status_callback("calibrating", None)

        calibration_chunks = int(0.4 / chunk_duration)
        noise_rms_list: list[float] = []

        try:
            with sd.InputStream(
                samplerate=sample_rate,
                channels=channels,
                dtype="int16",
                blocksize=chunk_samples,
            ) as stream:
                for _ in range(calibration_chunks):
                    frame, _ = stream.read(chunk_samples)
                    rms = self._calculate_rms(frame)
                    noise_rms_list.append(rms)

                ambient_noise = max(np.mean(noise_rms_list), 50.0) if noise_rms_list else 100.0
                speech_threshold = max(ambient_noise * 1.6, 250.0)

                if status_callback:
                    status_callback("listening", {"noise_floor": ambient_noise, "threshold": speech_threshold})

                recorded_frames: list[Any] = []
                speech_detected = False
                silence_start: float | None = None
                start_time = time.time()

                while True:
                    if stop_event and stop_event.is_set():
                        break

                    elapsed = time.time() - start_time
                    if elapsed > max_duration:
                        break

                    frame, _ = stream.read(chunk_samples)
                    rms = self._calculate_rms(frame)
                    recorded_frames.append(frame.copy())

                    if status_callback:
                        status_callback("audio_level", {"rms": rms, "speech": speech_detected})

                    if rms >= speech_threshold:
                        if not speech_detected:
                            speech_detected = True
                            if status_callback:
                                status_callback("speech_detected", {"rms": rms})
                        silence_start = None
                    else:
                        if speech_detected:
                            if silence_start is None:
                                silence_start = time.time()
                            elif (time.time() - silence_start) >= silence_limit:
                                break

            if not recorded_frames or not speech_detected:
                return None

            audio_data = np.concatenate(recorded_frames, axis=0)

            wav_io = io.BytesIO()
            sf.write(wav_io, audio_data, sample_rate, format="WAV", subtype="PCM_16")
            wav_io.seek(0)
            return wav_io.getvalue()

        except Exception as e:
            logger.error("microphone_record_error", error=str(e))
            return None

    @staticmethod
    def _calculate_rms(frame: Any) -> float:
        """Calculate Root Mean Square (RMS) energy of an audio frame."""
        if np is None or len(frame) == 0:
            return 0.0
        frame_float = frame.astype(np.float64)
        mean_sq = np.mean(frame_float ** 2)
        return float(math.sqrt(mean_sq))

    @staticmethod
    def bytes_to_base64(audio_bytes: bytes) -> str:
        """Encode audio bytes to Base64 string."""
        return base64.b64encode(audio_bytes).decode("utf-8")

    @staticmethod
    def base64_to_bytes(b64_str: str) -> bytes:
        """Decode Base64 string to audio bytes."""
        return base64.b64decode(b64_str)


# Global singleton instance
voice_service = VoiceService()
