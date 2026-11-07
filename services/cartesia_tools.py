"""Cartesia speech-to-text and text-to-speech for the product.

    transcribe           voice note -> text (ink-whisper)
    make_voice_message   render one fixed prompt line to an mp3

The live verification call does not use Cartesia. It plays the files
`scripts/render_prompts.py` writes. See services/CARTESIA.md.
"""
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY")
# Any voice from https://play.cartesia.ai/voices. The default (Whitney) is calm and even, for a worried student.
# "or" so a blank CARTESIA_VOICE_ID= line in .env still falls back to the default.
CARTESIA_VOICE_ID = os.getenv("CARTESIA_VOICE_ID") or "f3c7d5d2-c1e1-41a0-bd88-8b5512be5335"

CARTESIA_API = "https://api.cartesia.ai"
CARTESIA_VERSION = "2026-08-14"
SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

# The student answers the call and types the check code on the keypad; nobody nearby hears the digits.
OUTREACH_SCRIPT = (
    "Hi, this is Family Shield, an AI assistant calling for your family. "
    "They just got a message that says it's from you, and they want to make sure you're okay. "
    "Please enter your four-digit check code on your phone's keypad now."
)


def _headers() -> dict:
    if not CARTESIA_API_KEY:
        raise RuntimeError("Set CARTESIA_API_KEY in .env")
    return {"Authorization": f"Bearer {CARTESIA_API_KEY}", "Cartesia-Version": CARTESIA_VERSION}


def transcribe(audio_file_path: str, language: str = "en") -> str:
    """Turn a voice note into text with Cartesia speech-to-text.

    Accepts mp3, m4a, ogg, wav, webm and more. Pass language="hi" for a Hindi voice note.
    Blocking HTTP: from an async handler, call it as `await asyncio.to_thread(transcribe, path)`.
    """
    with open(audio_file_path, "rb") as audio:
        response = requests.post(
            f"{CARTESIA_API}/stt",
            headers=_headers(),
            files={"file": audio},
            data={"model": "ink-whisper", "language": language},
            timeout=60,
        )
    response.raise_for_status()
    return response.json()["text"]


def make_voice_message(
    text: str = OUTREACH_SCRIPT,
    out_path: str = str(SAMPLES_DIR / "outreach.mp3"),
    *,
    language: str = "en",
    voice_id: str | None = None,
) -> str:
    """Generate the outreach message as audio with Cartesia text-to-speech.

    Returns the path of the saved mp3 file (samples/outreach.mp3 unless out_path is given).
    `language` and `voice_id` default to the hackathon call's English voice; the product's
    Korean call prompts (scripts/render_prompts.py) pass `ko` and a Korean voice.
    """
    response = requests.post(
        f"{CARTESIA_API}/tts/bytes",
        headers=_headers(),
        json={
            "model_id": "sonic-3.6",
            "transcript": text,
            "voice": voice_id or CARTESIA_VOICE_ID,
            "language": language,
            "output_format": {"container": "mp3", "sample_rate": 44100, "bit_rate": 128000},
        },
        timeout=60,
    )
    response.raise_for_status()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(response.content)
    return out_path


if __name__ == "__main__":
    note = SAMPLES_DIR / "note-1.mp3"
    if note.exists():
        print(transcribe(str(note)))
    print(make_voice_message())
