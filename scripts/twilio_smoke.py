"""Manual Twilio checks for milestones 5 and 6. Sends real messages and calls.

    python -m scripts.twilio_smoke sms   +821012345678   # SMS OTP text, sample code
    python -m scripts.twilio_smoke voice +821012345678   # the same code read out by a call

Reads TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER (or
TWILIO_MESSAGING_SERVICE_SID for SMS) from .env. The code it sends is a
random sample and is not stored anywhere: this checks delivery to a +1 or
+82 handset, not the API. If the +82 SMS never arrives, try `voice`: that
is the fallback the API offers with `"channel": "voice"`.

The verification call itself (milestone 6) needs the API reachable at
PUBLIC_BASE_URL. See docs/MANUAL_CHECKS.md.
"""

import os
import sys

from dotenv import load_dotenv

from backend.enroll import TwilioOtp, new_otp_code, sms_language


def main(argv=None) -> int:
    load_dotenv()
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2 or args[0] not in ("sms", "voice"):
        print(__doc__)
        return 2
    channel, phone = args
    if not (phone.startswith("+1") or phone.startswith("+82")):
        print("Only +1 and +82 numbers are supported.", file=sys.stderr)
        return 2
    try:
        sender = TwilioOtp.from_env(os.environ)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 2
    code = new_otp_code()
    sender.send(phone, code, channel=channel)
    print(f"Sent a {channel} code ({sms_language(phone)}) to the number ending {phone[-4:]}: {code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
