"""Audio file utilities for the dictaphone feature."""

import datetime
import os
from pathlib import Path


RECORDINGS_DIR = Path("recordings")


def save_audio(audio_bytes: bytes, extension: str = "wav") -> Path:
    """Save raw audio bytes to a timestamped file in the recordings directory.

    Args:
        audio_bytes: Raw audio data from st.audio_input.
        extension: File extension (default: wav).

    Returns:
        Path to the saved file.
    """
    RECORDINGS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = RECORDINGS_DIR / f"recording_{timestamp}.{extension}"
    filename.write_bytes(audio_bytes)
    return filename


def list_recordings() -> list[Path]:
    """Return all recordings sorted by modification time (newest first)."""
    if not RECORDINGS_DIR.exists():
        return []
    files = sorted(
        RECORDINGS_DIR.glob("recording_*"),
        key=os.path.getmtime,
        reverse=True,
    )
    return files


def format_size(path: Path) -> str:
    """Return a human-readable file size string."""
    size = path.stat().st_size
    for unit in ("o", "Ko", "Mo"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} Go"
