"""Verification state machine. Pure: apply(case, event) -> case.

No database, network, telephony, push, or model calls. The caller loads a
row, calls apply, and writes the row back. See docs/PRODUCT_REDESIGN.md,
"Verification state machine".

States are opened, waiting_push, calling, awaiting_answer, confirmed, scam,
and not_confirmed. The last three are terminal. A later event returns the
same dict. A known event that does not apply does too. A transition returns
a new dict and does not mutate the input. Extra keys are copied through.

Only push_answered_yes, push_answered_no, answer_yes, and answer_no store
sent or not_sent. The keypad events count only in awaiting_answer, which
code_accepted enters. A keypad yes while number_recent is set is stored as
number_recent. A keypad no is still not_sent. A push yes is sent even when
the number is new. answered_via is set only for sent and not_sent.

There is no event for an inbound caller id. An unknown name raises
ValueError. This module does not generate codes, sleep, or count the
five-miss lock. number_recent and static_locked arrive on the case. A wrong,
used, or expired code arrives as code_rejected.
"""

_TERMINAL = frozenset({"confirmed", "scam", "not_confirmed"})
_PUSH_STATES = frozenset({"waiting_push", "calling", "awaiting_answer"})


def apply(case: dict, event: str) -> dict:
    if not isinstance(event, str):
        raise TypeError("event must be a str")
    if event not in _HANDLERS:
        raise ValueError(f"unknown event {event!r}")
    if case["state"] in _TERMINAL:
        return case
    updated = _HANDLERS[event](case)
    if updated is None:
        return case
    return updated


def _copy(case: dict, **changes) -> dict:
    updated = dict(case)
    updated.update(changes)
    return updated


def _enter_calling(case: dict) -> dict | None:
    """Place the fallback call, or refuse it when the static code is locked.

    Returns None when there is no opted-in phone. The caller then records
    no_number, unreachable, or timeout. A locked static code is not dialed
    from start, from a permanent push failure, or from the push window.
    An app-linked child still gets a one-time code; the lock does not
    apply to that channel.
    """
    if not case["has_opted_in_phone"]:
        return None
    if not case["has_app"] and case["static_locked"]:
        return _copy(case, state="not_confirmed", result="code_locked")
    channel = "one_time" if case["has_app"] else "static"
    return _copy(case, state="calling", code_channel=channel)


def _on_start(case: dict) -> dict | None:
    if case["state"] != "opened":
        return None
    if case["has_push_token"]:
        return _copy(case, state="waiting_push")
    calling = _enter_calling(case)
    if calling is not None:
        return calling
    return _copy(case, state="not_confirmed", result="no_number")


def _on_push_yes(case: dict) -> dict | None:
    if case["state"] not in _PUSH_STATES:
        return None
    return _copy(case, state="confirmed", result="sent", answered_via="push")


def _on_push_no(case: dict) -> dict | None:
    if case["state"] not in _PUSH_STATES:
        return None
    return _copy(case, state="scam", result="not_sent", answered_via="push")


def _on_push_failed(case: dict) -> dict | None:
    if case["state"] != "waiting_push":
        return None
    calling = _enter_calling(case)
    if calling is not None:
        return calling
    return _copy(case, state="not_confirmed", result="unreachable")


def _on_push_window(case: dict) -> dict | None:
    if case["state"] != "waiting_push":
        return None
    calling = _enter_calling(case)
    if calling is not None:
        return calling
    # The push was sent and nobody answered, and there is no number to dial.
    return _copy(case, state="not_confirmed", result="timeout")


def _on_call_accepted(_case: dict) -> dict | None:
    # The provider accepted the call. Legal in any open state, and it records
    # nothing: acceptance is the caller's signal to arm the code window.
    return None


def _on_call_failed(case: dict) -> dict | None:
    # Twilio's failed status, and only while the code is still being asked.
    # A drop after code_accepted is left to the answer window.
    if case["state"] != "calling":
        return None
    return _copy(case, state="not_confirmed", result="call_failed")


def _on_code_accepted(case: dict) -> dict | None:
    if case["state"] != "calling":
        return None
    return _copy(case, state="awaiting_answer")


def _on_code_rejected(case: dict) -> dict | None:
    # One wrong submission hangs up. The hackathon retry is not this machine.
    if case["state"] != "calling":
        return None
    return _copy(case, state="not_confirmed", result="wrong")


def _on_use_static_code(case: dict) -> dict | None:
    # Star during the one-time gather. A second star, or star on a call that
    # is already asking for the static code, changes nothing.
    if case["state"] != "calling" or case["code_channel"] != "one_time":
        return None
    if case["static_locked"]:
        return _copy(case, state="not_confirmed", result="code_locked")
    return _copy(case, code_channel="static")


def _on_code_check_slow(case: dict) -> dict | None:
    # The hash check missed its 4s budget. The first one replays the same
    # gather and is not a wrong code. The second ends the case.
    if case["state"] != "calling":
        return None
    seen = case["slow_checks"] + 1
    if seen >= 2:
        return _copy(
            case, state="not_confirmed", result="timeout", slow_checks=seen
        )
    return _copy(case, slow_checks=seen)


def _on_answer_yes(case: dict) -> dict | None:
    if case["state"] != "awaiting_answer":
        return None
    if case["number_recent"]:
        return _copy(case, state="not_confirmed", result="number_recent")
    return _copy(case, state="confirmed", result="sent", answered_via="call")


def _on_answer_no(case: dict) -> dict | None:
    if case["state"] != "awaiting_answer":
        return None
    return _copy(case, state="scam", result="not_sent", answered_via="call")


def _on_answer_unclear(case: dict) -> dict | None:
    if case["state"] != "awaiting_answer":
        return None
    return _copy(case, state="not_confirmed", result="no_answer")


def _on_answer_window(case: dict) -> dict | None:
    if case["state"] != "awaiting_answer":
        return None
    return _copy(case, state="not_confirmed", result="no_answer")


def _on_code_window(case: dict) -> dict | None:
    if case["state"] != "calling":
        return None
    return _copy(case, state="not_confirmed", result="timeout")


def _on_cancel(case: dict) -> dict | None:
    return _copy(case, state="not_confirmed", result="timeout")


_HANDLERS = {
    "start": _on_start,
    "push_answered_yes": _on_push_yes,
    "push_answered_no": _on_push_no,
    "push_failed": _on_push_failed,
    "push_window_elapsed": _on_push_window,
    "call_accepted": _on_call_accepted,
    "call_failed": _on_call_failed,
    "code_accepted": _on_code_accepted,
    "code_rejected": _on_code_rejected,
    "use_static_code": _on_use_static_code,
    "code_check_slow": _on_code_check_slow,
    "answer_yes": _on_answer_yes,
    "answer_no": _on_answer_no,
    "answer_unclear": _on_answer_unclear,
    "answer_window_elapsed": _on_answer_window,
    "code_window_elapsed": _on_code_window,
    "cancel": _on_cancel,
}
