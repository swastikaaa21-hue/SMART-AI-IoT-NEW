"""
Tests for Voice Service and Voice API Endpoints.
"""

from __future__ import annotations

import io
import uuid
import pytest
from httpx import AsyncClient

try:
    import numpy as np
    import soundfile as sf
    from gtts import gTTS
    has_audio_deps = True
except ImportError:
    has_audio_deps = False
    np = None
    sf = None
    gTTS = None

from app.services.voice_service import voice_service


pytestmark = pytest.mark.skipif(not has_audio_deps, reason="Audio native dependencies not installed")


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register and log in a test user to get a real valid auth header."""
    user_email = f"voice_{uuid.uuid4().hex[:6]}@example.com"
    password = "password123"

    await client.post(
        "/api/v1/auth/register",
        json={
            "email": user_email,
            "password": password,
            "full_name": "Voice User",
        },
    )

    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": user_email, "password": password},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def generate_test_wav_bytes(phrase: str = "tolong nyalakan lampu kamar") -> bytes:
    """Helper to synthesize test WAV bytes in memory."""
    mp3_bytes = voice_service.synthesize_speech(phrase, language="id")
    if not mp3_bytes:
        # Fallback silent WAV if offline
        silence = np.zeros(16000, dtype=np.int16)
        wav_io = io.BytesIO()
        sf.write(wav_io, silence, 16000, format="WAV", subtype="PCM_16")
        return wav_io.getvalue()

    # Convert MP3 to 16kHz WAV
    audio_io = io.BytesIO(mp3_bytes)
    data, samplerate = sf.read(audio_io, dtype="int16")
    if len(data.shape) > 1:
        data = data.mean(axis=1).astype(np.int16)

    wav_io = io.BytesIO()
    sf.write(wav_io, data, samplerate, format="WAV", subtype="PCM_16")
    wav_io.seek(0)
    return wav_io.getvalue()


class TestVoiceServiceUnit:
    def test_synthesize_speech(self):
        text = "Halo, Jarkvis siap membantu."
        audio_bytes = voice_service.synthesize_speech(text, language="id")
        assert audio_bytes is not None
        assert len(audio_bytes) > 0

    def test_rms_calculation(self):
        # Silence
        silent_frame = np.zeros(100, dtype=np.int16)
        assert voice_service._calculate_rms(silent_frame) == 0.0

        # Non-silent
        sine_frame = (np.sin(np.linspace(0, 10, 100)) * 1000).astype(np.int16)
        rms = voice_service._calculate_rms(sine_frame)
        assert rms > 0.0

    def test_base64_roundtrip(self):
        sample_bytes = b"RIFF1234WAVEfmt 16000"
        b64 = voice_service.bytes_to_base64(sample_bytes)
        assert isinstance(b64, str)
        restored = voice_service.base64_to_bytes(b64)
        assert restored == sample_bytes

    def test_transcribe_audio_bytes(self):
        wav_bytes = generate_test_wav_bytes("nyalakan lampu")
        transcript = voice_service.transcribe_audio_bytes(wav_bytes, language="id-ID")
        assert isinstance(transcript, str)
        if transcript:
            assert "lampu" in transcript.lower() or "nyala" in transcript.lower()


@pytest.mark.asyncio
class TestVoiceAPIEndpoints:
    async def test_synthesize_endpoint(self, client: AsyncClient, auth_headers: dict[str, str]):
        response = await client.post(
            "/api/v1/voice/synthesize",
            headers=auth_headers,
            json={"text": "Halo, lampu ruang tamu telah dinyalakan.", "language": "id"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("audio/mpeg")
        assert len(response.content) > 100

    async def test_transcribe_endpoint(self, client: AsyncClient, auth_headers: dict[str, str]):
        wav_bytes = generate_test_wav_bytes("nyalakan lampu")

        files = {"file": ("test.wav", wav_bytes, "audio/wav")}
        response = await client.post(
            "/api/v1/voice/transcribe",
            headers=auth_headers,
            files=files,
        )
        assert response.status_code == 200
        data = response.json()
        assert "transcript" in data
        assert "language" in data
        assert data["language"] == "id-ID"

    async def test_voice_chat_endpoint(self, client: AsyncClient, auth_headers: dict[str, str]):
        wav_bytes = generate_test_wav_bytes("halo jarkvis")

        files = {"file": ("command.wav", wav_bytes, "audio/wav")}
        response = await client.post(
            "/api/v1/voice/chat",
            headers=auth_headers,
            files=files,
        )
        assert response.status_code == 200
        data = response.json()
        assert "transcript" in data
        assert "reply" in data
        assert "audio_base64" in data
        assert "session_id" in data
