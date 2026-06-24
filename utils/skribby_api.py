"""Client pour l'API officielle Skribby."""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://platform.skribby.io/api/v1"

PLATFORM_MAP = {
    "zoom":  "zoom",
    "teams": "teams",
    "meet":  "gmeet",
}

PLATFORM_LABELS = {
    "zoom":  "🔵 Zoom",
    "teams": "🟣 Microsoft Teams",
    "meet":  "🟢 Google Meet",
}


def _headers() -> dict:
    key = os.getenv("SKRIBBY_API_KEY", "")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def detect_platform(url: str) -> str:
    url = url.lower()
    if "zoom.us" in url or "zoomgov.com" in url:
        return "zoom"
    if "teams.microsoft.com" in url or "teams.live.com" in url:
        return "teams"
    if "meet.google.com" in url:
        return "meet"
    return "unknown"


def create_bot(
    meeting_url: str,
    bot_name: str = "Skribby",
    platform: str | None = None,
) -> dict:
    """Crée un bot Skribby et le fait rejoindre la réunion."""
    if platform is None:
        platform = detect_platform(meeting_url)

    service = PLATFORM_MAP.get(platform, platform)

    payload = {
        "meeting_url": meeting_url,
        "bot_name": bot_name,
        "service": service,
        "transcription_model": "none",
    }

    resp = requests.post(f"{BASE_URL}/bot", headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_bot(bot_id: str) -> dict:
    """Récupère le statut et les données d'un bot."""
    resp = requests.get(f"{BASE_URL}/bot/{bot_id}", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def stop_bot(bot_id: str) -> dict:
    """Arrête un bot en cours de réunion. Ignore les erreurs si déjà terminé."""
    resp = requests.post(f"{BASE_URL}/bot/{bot_id}/stop", headers=_headers(), timeout=15)
    if resp.status_code in (403, 404, 409):
        # Bot déjà terminé ou non trouvé — on récupère juste les données
        return get_bot(bot_id)
    resp.raise_for_status()
    return resp.json()


def delete_bot(bot_id: str) -> None:
    """Supprime un bot et ses données."""
    requests.delete(f"{BASE_URL}/bot/{bot_id}", headers=_headers(), timeout=15)


def wait_for_status(bot_id: str, target_statuses: list[str], timeout: int = 120) -> dict:
    """Attend qu'un bot atteigne un des statuts cibles."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = get_bot(bot_id)
        if data.get("status") in target_statuses:
            return data
        time.sleep(3)
    return get_bot(bot_id)


def get_recording_url(bot_data: dict) -> str | None:
    """Extrait l'URL de l'enregistrement audio depuis les données du bot."""
    return (
        bot_data.get("recording_url")
        or bot_data.get("audio_url")
        or bot_data.get("media_url")
    )


def download_audio(url: str) -> bytes:
    """Télécharge l'audio depuis l'URL fournie par Skribby."""
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return resp.content
