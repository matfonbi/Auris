"""Transcription audio via l'API Mistral (Voxtral)."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

MISTRAL_BASE_URL = "https://api.mistral.ai/v1"
MISTRAL_MODEL = "voxtral-mini-2507"


def _headers() -> dict:
    key = os.getenv("MISTRAL_API_KEY", "")
    return {"Authorization": f"Bearer {key}"}


def _format_diarized(result: dict) -> str:
    """Formate une réponse diarisée en texte lisible [Speaker X]: ..."""
    segments = result.get("segments") or result.get("diarization") or []
    if not segments:
        return result.get("text", "")

    lines = []
    for seg in segments:
        speaker = seg.get("speaker", seg.get("speaker_id", "?"))
        text = seg.get("text", "").strip()
        if text:
            lines.append(f"[{speaker}] {text}")
    return "\n".join(lines)


def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "recording.webm",
    language: str | None = None,
    diarization: bool = True,
) -> str:
    """Transcrit un fichier audio via l'API Mistral.

    Avec diarization=True, chaque réplique est préfixée par le locuteur.
    """
    files = {"file": (filename, audio_bytes, "audio/webm")}
    data: dict = {"model": MISTRAL_MODEL, "diarization": True}
    if language:
        data["language"] = language

    resp = requests.post(
        f"{MISTRAL_BASE_URL}/audio/transcriptions",
        headers=_headers(),
        files=files,
        data=data,
        timeout=300,
    )
    resp.raise_for_status()
    result = resp.json()

    if diarization:
        return _format_diarized(result)
    return result.get("text", "")
