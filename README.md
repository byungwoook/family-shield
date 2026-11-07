# Family Shield

Check with your child before you send money.

A parent got a message that sounds like their child and asks for money. The voice can be cloned, and the caller ID can show the child's real number. Family Shield does not decide whether a voice is real. The parent picks a child they already linked, attaches the message, and taps Verify. The child answers in the app after Face ID or a fingerprint. If they do not answer in time, or they have no app, the backend calls the phone number that child already proved they control. That call is a fixed recording plus keypad digits. Claude reads the message for the parent's information. Only the child's authenticated answer changes the result.

| Result | Meaning |
| --- | --- |
| Confirmed | The child authenticated and said they asked for the money. Talk to them directly before sending anything. |
| Scam | The child authenticated and said they did not ask. Do not send money and do not reply to the sender. |
| Not confirmed | Wrong code, no answer, no number, a number registered or changed in the last 24 hours, or anything else that is not a clear answer. Do not send money. |

An incoming call, a caller-ID string, and a number written inside the message are not evidence. The iOS and Android apps can label one number, the number Family Shield calls from, as "Family Shield", so the child can tell that call from an unknown caller. They do not label the child's number, and they do not say any other caller is genuine. The check code works without that label.

## Where the code is

| Piece | Where |
| --- | --- |
| API | `backend/` (FastAPI and Postgres). The client contract is [docs/API_CONTRACT.md](docs/API_CONTRACT.md). |
| Android | `android/` (Kotlin, parent and child in one app). |
| iOS | `ios/project.yml` generates the Xcode project. Logic that does not need UIKit is the Swift package `ios/FamilyShieldCore`. |
| Design | [docs/PRODUCT_REDESIGN.md](docs/PRODUCT_REDESIGN.md). |
| Where the work stands | [docs/CHECKPOINT.md](docs/CHECKPOINT.md). |
| Handset checks | [docs/MANUAL_CHECKS.md](docs/MANUAL_CHECKS.md). |

v1 does not move money. Safe Wallet is not in this tree.

## Run the tests

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
docker compose up -d          # Postgres 16; see docs/CHECKPOINT.md if you use a local server instead
PGTZ=UTC venv/bin/python -m pytest
make check                    # the same pytest run
```

`PGTZ=UTC` matters. A Postgres session in another time zone fails two tests in `tests/test_me.py`.

```bash
cd android && ./gradlew assembleDebug testDebugUnitTest
cd ios/FamilyShieldCore && swift test
```

There is no Xcode project in git. On a Mac, `xcodegen generate` in `ios/` builds it from `ios/project.yml`.

## Hackathon demo (archived)

This repository started as a Cal Hacks 13.0 demo: five Fetch.ai agents in ASI:One, with Moss, Apify, a Supabase voice-note bucket, and a Cartesia voice agent on the call. That code is the git tag [`hackathon-demo`](https://github.com/byungwoook/family-shield/tree/hackathon-demo) on this fork. The tag is commit `c81c9c9`, the last commit that still contains `agents/`. Check out the tag to read or run the demo. The tag is not on the upstream repository.

The original project is [khuzaymaa918/family-shield](https://github.com/khuzaymaa918/family-shield). It won a Special Mention in Fetch.ai's Best Use of ASI category. The team was Khuzayma Mushtaq, Jione Park, Byungwook Kang, and Oluwamurewa Fadare.
