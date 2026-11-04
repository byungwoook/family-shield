"""Render the twelve fallback-call prompts with Cartesia (milestone 6).

    python -m scripts.render_prompts            # writes the missing files
    python -m scripts.render_prompts --force    # rewrites all twelve

Needs CARTESIA_API_KEY. English uses CARTESIA_VOICE_ID (default Whitney).
Korean needs CARTESIA_VOICE_ID_KO, a Korean Sonic voice from
https://play.cartesia.ai/voices; there is no default, so a Korean child is
never read to by an English voice by accident.

Each line in backend.calls.PROMPT_LINES is one `make_voice_message` call.
The files land in backend/prompts/{en,ko}/{name}.mp3 and are checked in.
The live call only plays them. Listen to all twelve before committing.
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from backend.calls import LANGUAGES, PROMPT_LINES, PROMPT_NAMES, prompt_path


def main(argv=None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="rewrite files that exist")
    args = parser.parse_args(argv)

    if not os.getenv("CARTESIA_API_KEY"):
        print("Set CARTESIA_API_KEY first.", file=sys.stderr)
        return 2
    korean_voice = (os.getenv("CARTESIA_VOICE_ID_KO") or "").strip()
    if not korean_voice:
        print("Set CARTESIA_VOICE_ID_KO to a Korean voice first.", file=sys.stderr)
        return 2

    # Imported here so --help works without the hackathon environment.
    from services.cartesia_tools import make_voice_message

    voices = {"en": None, "ko": korean_voice}
    written = 0
    for language in LANGUAGES:
        for name in PROMPT_NAMES:
            path = prompt_path(language, name)
            if path.is_file() and path.stat().st_size > 0 and not args.force:
                continue
            make_voice_message(
                PROMPT_LINES[language][name],
                str(path),
                language=language,
                voice_id=voices[language],
            )
            written += 1
            print(f"wrote {language}/{name}.mp3")
    print(f"{written} file(s) written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
