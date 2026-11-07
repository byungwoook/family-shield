# Cartesia in Family Shield

The product uses Cartesia for two jobs, both ahead of or beside the verification call. The call itself is Twilio: a fixed mp3 and keypad digits (`backend/calls.py`). There is no voice agent and no model on the call.

| Job | Where | What it does |
| --- | --- | --- |
| Batch speech-to-text (`ink-whisper`) | `transcribe` in `services/cartesia_tools.py` | Turns a voice note into text. Pass `language="ko"` for a Korean note, otherwise `en`. |
| Text-to-speech (`sonic-3.6`) | `make_voice_message` | Renders the twelve prompt files once (`python -m scripts.render_prompts`). English uses Whitney (`f3c7d5d2-c1e1-41a0-bd88-8b5512be5335`) unless `CARTESIA_VOICE_ID` is set. Korean uses `CARTESIA_VOICE_ID_KO`. |

The live call plays those files. A Cartesia outage can block transcription of a new voice note. It cannot block a call whose recordings are already on disk.

## Hackathon demo (archived)

The Cal Hacks call was a Cartesia managed agent with Claude as its model. That setup, including `cartesia_setup.py` and `deliver_voice_message`, is on the git tag `hackathon-demo` (commit `c81c9c9` on this fork). It is not in this tree.
