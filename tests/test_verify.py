"""Tests for the milestone-1 verification state machine.

The contract is docs/PRODUCT_REDESIGN.md, section "Verification state machine".
Events are the strings named there. `push_answered_yes` / `push_answered_no`
are the in-app answer. `answer_yes` / `answer_no` / `answer_unclear` are the
keypad, and they count only after `code_accepted`.

A few results are named in the prose but not given their own event. The tests
lock the reading used here:

- `push_failed` with no opted-in phone is `unreachable`. The 90s push window
  with no phone is `timeout`. Both are yellow.
- `code_locked` replaces a call we would have placed. No push token and no
  opted-in phone is `no_number`, even if the static code is also locked.
- `call_accepted` changes no field. `no-answer` / `busy` have no event in the
  milestone-1 list; `code_window_elapsed` is the named timeout while calling.
- `call_failed` ends `calling` only. After the code is accepted, that event
  does not invent a verdict.
- `answered_via` is set only for `sent` and `not_sent`.
"""

import ast
from pathlib import Path

import pytest

from backend.verify import apply


EVENTS = (
    "start",
    "push_answered_yes",
    "push_answered_no",
    "push_failed",
    "push_window_elapsed",
    "call_accepted",
    "call_failed",
    "code_accepted",
    "code_rejected",
    "use_static_code",
    "code_check_slow",
    "answer_yes",
    "answer_no",
    "answer_unclear",
    "answer_window_elapsed",
    "code_window_elapsed",
    "cancel",
)

OPEN_STATES = ("opened", "waiting_push", "calling", "awaiting_answer")

# (state, event) -> fields that change on an armed case. Every other pair of
# an open state and a known event must return the same dict.
LEGAL = {
    ("opened", "start"): {"state": "waiting_push"},
    ("opened", "cancel"): {"state": "not_confirmed", "result": "timeout"},
    ("waiting_push", "push_answered_yes"): {
        "state": "confirmed",
        "result": "sent",
        "answered_via": "push",
    },
    ("waiting_push", "push_answered_no"): {
        "state": "scam",
        "result": "not_sent",
        "answered_via": "push",
    },
    ("waiting_push", "push_failed"): {
        "state": "calling",
        "code_channel": "one_time",
        "result": None,
    },
    ("waiting_push", "push_window_elapsed"): {
        "state": "calling",
        "code_channel": "one_time",
        "result": None,
    },
    ("waiting_push", "cancel"): {"state": "not_confirmed", "result": "timeout"},
    ("calling", "push_answered_yes"): {
        "state": "confirmed",
        "result": "sent",
        "answered_via": "push",
    },
    ("calling", "push_answered_no"): {
        "state": "scam",
        "result": "not_sent",
        "answered_via": "push",
    },
    ("calling", "call_failed"): {"state": "not_confirmed", "result": "call_failed"},
    ("calling", "code_accepted"): {"state": "awaiting_answer", "result": None},
    ("calling", "code_rejected"): {
        "state": "not_confirmed",
        "result": "wrong",
        "code_channel": "one_time",
    },
    ("calling", "use_static_code"): {
        "state": "calling",
        "code_channel": "static",
        "result": None,
        "slow_checks": 0,
    },
    ("calling", "code_check_slow"): {
        "state": "calling",
        "result": None,
        "slow_checks": 1,
    },
    ("calling", "code_window_elapsed"): {"state": "not_confirmed", "result": "timeout"},
    ("calling", "cancel"): {"state": "not_confirmed", "result": "timeout"},
    ("awaiting_answer", "push_answered_yes"): {
        "state": "confirmed",
        "result": "sent",
        "answered_via": "push",
    },
    ("awaiting_answer", "push_answered_no"): {
        "state": "scam",
        "result": "not_sent",
        "answered_via": "push",
    },
    ("awaiting_answer", "answer_yes"): {
        "state": "confirmed",
        "result": "sent",
        "answered_via": "call",
    },
    ("awaiting_answer", "answer_no"): {
        "state": "scam",
        "result": "not_sent",
        "answered_via": "call",
    },
    ("awaiting_answer", "answer_unclear"): {
        "state": "not_confirmed",
        "result": "no_answer",
    },
    ("awaiting_answer", "answer_window_elapsed"): {
        "state": "not_confirmed",
        "result": "no_answer",
    },
    ("awaiting_answer", "cancel"): {"state": "not_confirmed", "result": "timeout"},
}

NO_OPS = [
    (state, event)
    for state in OPEN_STATES
    for event in EVENTS
    if (state, event) not in LEGAL
]

YELLOW = frozenset({
    "wrong",
    "no_answer",
    "no_number",
    "call_failed",
    "timeout",
    "unreachable",
    "code_locked",
    "number_recent",
})


def case(**overrides):
    base = {
        "state": "opened",
        "result": None,
        "answered_via": None,
        "code_channel": None,
        "has_app": False,
        "has_push_token": False,
        "has_opted_in_phone": False,
        "number_recent": False,
        "static_locked": False,
        "slow_checks": 0,
    }
    base.update(overrides)
    return base


def armed(state, **overrides):
    """A case in `state` with every flag set so a legal event can fire."""
    base = case(
        state=state,
        has_app=True,
        has_push_token=True,
        has_opted_in_phone=True,
    )
    if state in ("calling", "awaiting_answer"):
        base["code_channel"] = "one_time"
    base.update(overrides)
    return base


def assert_consistent(current):
    if current["state"] == "confirmed":
        assert current["result"] == "sent"
        assert current["answered_via"] in ("push", "call")
    elif current["state"] == "scam":
        assert current["result"] == "not_sent"
        assert current["answered_via"] in ("push", "call")
    elif current["state"] == "not_confirmed":
        assert current["result"] in YELLOW
        assert current["answered_via"] is None
    else:
        assert current["state"] in OPEN_STATES
        assert current["result"] is None
        assert current["answered_via"] is None


def test_every_open_state_and_event_is_classified_once():
    classified = set(LEGAL) | set(NO_OPS)
    assert classified == {(state, event) for state in OPEN_STATES for event in EVENTS}
    assert set(LEGAL).isdisjoint(NO_OPS)


@pytest.mark.parametrize(("state", "event"), list(LEGAL))
def test_legal_transition(state, event):
    before = armed(state)
    snapshot = dict(before)
    after = apply(before, event)
    assert before == snapshot
    assert after is not before
    expect = LEGAL[(state, event)]
    for key, value in expect.items():
        assert after[key] == value
    for key, value in before.items():
        if key not in expect:
            assert after[key] == value
    assert_consistent(after)


@pytest.mark.parametrize(("state", "event"), NO_OPS)
def test_ignored_event_returns_the_same_case(state, event):
    before = armed(state)
    assert apply(before, event) is before


@pytest.mark.parametrize(
    ("state", "result", "via"),
    [
        ("confirmed", "sent", "push"),
        ("scam", "not_sent", "call"),
        ("not_confirmed", "wrong", None),
        ("not_confirmed", "number_recent", None),
        ("not_confirmed", "timeout", None),
    ],
)
@pytest.mark.parametrize("event", EVENTS)
def test_terminal_event_returns_the_same_case(state, result, via, event):
    done = case(
        state=state,
        result=result,
        answered_via=via,
        code_channel="one_time",
        slow_checks=1,
        number_recent=True,
    )
    assert apply(done, event) is done


def test_verify_module_does_no_io():
    source = Path("backend/verify.py").read_text()
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert imported == []


# --- Edges named in the milestone ---


def test_unanswered_call_is_timeout_never_not_sent():
    calling = case(state="calling", code_channel="static", has_opted_in_phone=True)
    assert apply(calling, "call_accepted") is calling
    done = apply(calling, "code_window_elapsed")
    assert done["state"] == "not_confirmed"
    assert done["result"] == "timeout"
    assert done["result"] != "not_sent"
    assert_consistent(done)


def test_one_wrong_code_ends_the_case_immediately():
    calling = case(state="calling", code_channel="static", has_app=False)
    done = apply(calling, "code_rejected")
    assert done["state"] == "not_confirmed"
    assert done["result"] == "wrong"
    assert done["static_locked"] is False
    assert apply(done, "code_rejected") is done
    assert apply(done, "code_accepted") is done
    assert apply(done, "answer_yes") is done
    assert_consistent(done)


def test_star_switches_one_time_channel_to_static():
    calling = case(
        state="calling",
        code_channel="one_time",
        has_app=True,
        static_locked=False,
    )
    switched = apply(calling, "use_static_code")
    assert switched is not calling
    assert switched["state"] == "calling"
    assert switched["code_channel"] == "static"
    assert switched["result"] is None
    assert switched["slow_checks"] == 0
    assert apply(switched, "use_static_code") is switched


def test_star_on_the_static_channel_changes_nothing():
    calling = case(state="calling", code_channel="static", has_app=False)
    assert apply(calling, "use_static_code") is calling


def test_star_when_static_code_is_locked_ends_without_a_guess():
    calling = case(
        state="calling",
        code_channel="one_time",
        has_app=True,
        static_locked=True,
    )
    done = apply(calling, "use_static_code")
    assert done["state"] == "not_confirmed"
    assert done["result"] == "code_locked"
    assert done["result"] != "wrong"
    assert done["code_channel"] == "one_time"
    assert_consistent(done)


def test_entering_calling_picks_one_time_code_for_an_app_child():
    after = apply(
        case(has_app=True, has_push_token=False, has_opted_in_phone=True),
        "start",
    )
    assert after["state"] == "calling"
    assert after["code_channel"] == "one_time"
    assert after["result"] is None


def test_entering_calling_picks_static_code_without_an_app():
    after = apply(
        case(has_app=False, has_push_token=False, has_opted_in_phone=True),
        "start",
    )
    assert after["state"] == "calling"
    assert after["code_channel"] == "static"
    assert after["result"] is None


@pytest.mark.parametrize("event", ["push_failed", "push_window_elapsed"])
def test_fallback_call_uses_the_channel_for_that_child(event):
    app_child = case(
        state="waiting_push",
        has_app=True,
        has_push_token=True,
        has_opted_in_phone=True,
    )
    no_app = case(
        state="waiting_push",
        has_app=False,
        has_push_token=True,
        has_opted_in_phone=True,
    )
    assert apply(app_child, event)["code_channel"] == "one_time"
    assert apply(no_app, event)["code_channel"] == "static"
    assert apply(app_child, event)["state"] == "calling"
    assert apply(no_app, event)["state"] == "calling"


@pytest.mark.parametrize("state", ["opened", "waiting_push", "calling"])
@pytest.mark.parametrize("event", ["answer_yes", "answer_no", "answer_unclear"])
def test_keypad_answer_before_the_code_changes_nothing(state, event):
    before = armed(state, number_recent=True)
    assert apply(before, event) is before
    assert before["result"] is None


def test_unclear_answer_is_no_answer_not_a_scam():
    done = apply(armed("awaiting_answer"), "answer_unclear")
    assert done["state"] == "not_confirmed"
    assert done["result"] == "no_answer"
    assert done["result"] != "not_sent"
    assert apply(done, "answer_no") is done
    assert_consistent(done)


def test_answer_window_is_no_answer_never_a_no():
    done = apply(armed("awaiting_answer"), "answer_window_elapsed")
    assert done["state"] == "not_confirmed"
    assert done["result"] == "no_answer"
    assert done["result"] != "not_sent"
    assert_consistent(done)


def test_push_yes_is_confirmed_and_a_later_no_is_ignored():
    done = apply(armed("waiting_push"), "push_answered_yes")
    assert done["state"] == "confirmed"
    assert done["result"] == "sent"
    assert done["answered_via"] == "push"
    assert done["code_channel"] is None
    assert apply(done, "answer_no") is done
    assert apply(done, "push_answered_no") is done


def test_call_yes_on_a_recent_number_is_yellow():
    done = apply(armed("awaiting_answer", number_recent=True), "answer_yes")
    assert done["state"] == "not_confirmed"
    assert done["result"] == "number_recent"
    assert done["state"] != "confirmed"
    assert done["result"] != "sent"
    assert done["answered_via"] is None
    assert_consistent(done)


def test_call_no_on_a_recent_number_stays_red():
    done = apply(armed("awaiting_answer", number_recent=True), "answer_no")
    assert done["state"] == "scam"
    assert done["result"] == "not_sent"
    assert done["answered_via"] == "call"
    assert_consistent(done)


@pytest.mark.parametrize("state", ["waiting_push", "calling", "awaiting_answer"])
def test_push_yes_stays_green_when_the_number_is_recent(state):
    done = apply(armed(state, number_recent=True), "push_answered_yes")
    assert done["state"] == "confirmed"
    assert done["result"] == "sent"
    assert done["answered_via"] == "push"


@pytest.mark.parametrize("state", ["waiting_push", "calling", "awaiting_answer"])
def test_push_no_stays_red_when_the_number_is_recent(state):
    done = apply(armed(state, number_recent=True), "push_answered_no")
    assert done["state"] == "scam"
    assert done["result"] == "not_sent"
    assert done["answered_via"] == "push"


def test_push_yes_during_the_call_ignores_a_later_wrong_code():
    done = apply(armed("calling"), "push_answered_yes")
    assert done["state"] == "confirmed"
    assert done["result"] == "sent"
    assert done["answered_via"] == "push"
    assert apply(done, "code_rejected") is done
    assert apply(done, "code_accepted") is done
    assert apply(done, "answer_no") is done


def test_push_yes_after_the_right_code_beats_a_later_keypad_no():
    waiting = apply(armed("calling"), "code_accepted")
    assert waiting["state"] == "awaiting_answer"
    done = apply(waiting, "push_answered_yes")
    assert done["state"] == "confirmed"
    assert done["result"] == "sent"
    assert done["answered_via"] == "push"
    assert apply(done, "answer_no") is done
    assert apply(done, "answer_yes") is done


def test_start_with_nothing_reachable_is_no_number():
    done = apply(case(has_push_token=False, has_opted_in_phone=False), "start")
    assert done["state"] == "not_confirmed"
    assert done["result"] == "no_number"
    assert done["code_channel"] is None
    assert_consistent(done)


def test_start_with_no_app_and_locked_static_code_does_not_call():
    done = apply(
        case(
            has_app=False,
            has_push_token=False,
            has_opted_in_phone=True,
            static_locked=True,
        ),
        "start",
    )
    assert done["state"] == "not_confirmed"
    assert done["result"] == "code_locked"
    assert done["code_channel"] is None
    assert done["state"] != "calling"
    assert_consistent(done)


def test_locked_code_without_a_phone_is_no_number():
    done = apply(
        case(
            has_app=False,
            has_push_token=False,
            has_opted_in_phone=False,
            static_locked=True,
        ),
        "start",
    )
    assert done["state"] == "not_confirmed"
    assert done["result"] == "no_number"


def test_locked_static_code_does_not_block_an_app_child():
    waiting = apply(
        case(
            has_app=True,
            has_push_token=True,
            has_opted_in_phone=True,
            static_locked=True,
        ),
        "start",
    )
    assert waiting["state"] == "waiting_push"
    assert waiting["result"] is None
    calling = apply(
        case(
            has_app=True,
            has_push_token=False,
            has_opted_in_phone=True,
            static_locked=True,
        ),
        "start",
    )
    assert calling["state"] == "calling"
    assert calling["code_channel"] == "one_time"
    assert calling["result"] is None


@pytest.mark.parametrize("event", ["push_failed", "push_window_elapsed"])
def test_fallback_does_not_dial_when_the_static_code_is_locked(event):
    before = case(
        state="waiting_push",
        has_app=False,
        has_push_token=True,
        has_opted_in_phone=True,
        static_locked=True,
    )
    done = apply(before, event)
    assert done["state"] == "not_confirmed"
    assert done["result"] == "code_locked"
    assert done["code_channel"] is None
    assert_consistent(done)


def test_push_failure_with_no_phone_is_unreachable():
    done = apply(
        case(state="waiting_push", has_push_token=True, has_opted_in_phone=False),
        "push_failed",
    )
    assert done["state"] == "not_confirmed"
    assert done["result"] == "unreachable"
    assert_consistent(done)


def test_push_failure_with_no_phone_stays_unreachable_when_locked():
    done = apply(
        case(
            state="waiting_push",
            has_app=False,
            has_push_token=True,
            has_opted_in_phone=False,
            static_locked=True,
        ),
        "push_failed",
    )
    assert done["result"] == "unreachable"


def test_push_window_with_no_phone_stays_timeout_when_locked():
    done = apply(
        case(
            state="waiting_push",
            has_app=False,
            has_push_token=True,
            has_opted_in_phone=False,
            static_locked=True,
        ),
        "push_window_elapsed",
    )
    assert done["result"] == "timeout"
    assert done["result"] != "code_locked"


def test_push_window_with_no_phone_is_timeout():
    done = apply(
        case(state="waiting_push", has_push_token=True, has_opted_in_phone=False),
        "push_window_elapsed",
    )
    assert done["state"] == "not_confirmed"
    assert done["result"] == "timeout"
    assert done["result"] != "unreachable"
    assert done["result"] != "not_sent"
    assert_consistent(done)


def test_start_asks_in_the_app_before_calling():
    after = apply(
        case(has_app=True, has_push_token=True, has_opted_in_phone=True),
        "start",
    )
    assert after["state"] == "waiting_push"
    assert after["code_channel"] is None
    assert after["result"] is None


def test_answering_the_push_does_not_open_a_call():
    started = apply(
        case(has_app=True, has_push_token=True, has_opted_in_phone=True),
        "start",
    )
    done = apply(started, "push_answered_yes")
    assert done["state"] == "confirmed"
    assert done["result"] == "sent"
    assert done["answered_via"] == "push"
    assert done["code_channel"] is None


def test_first_slow_check_replays_and_the_second_times_out():
    calling = case(state="calling", code_channel="one_time", has_app=True)
    once = apply(calling, "code_check_slow")
    assert once["state"] == "calling"
    assert once["result"] is None
    assert once["slow_checks"] == 1
    assert once["code_channel"] == "one_time"
    assert apply(once, "code_accepted")["state"] == "awaiting_answer"
    rejected = apply(once, "code_rejected")
    assert rejected["result"] == "wrong"
    assert rejected["slow_checks"] == 1
    twice = apply(once, "code_check_slow")
    assert twice["state"] == "not_confirmed"
    assert twice["result"] == "timeout"
    assert twice["result"] != "wrong"
    assert twice["slow_checks"] == 2
    assert_consistent(twice)


def test_failed_call_is_yellow_never_a_no():
    done = apply(armed("calling"), "call_failed")
    assert done["state"] == "not_confirmed"
    assert done["result"] == "call_failed"
    assert done["result"] != "not_sent"
    assert_consistent(done)


def test_call_drop_after_the_code_does_not_invent_a_verdict():
    waiting = armed("awaiting_answer")
    assert apply(waiting, "call_failed") is waiting


def test_code_window_does_not_preempt_the_answer_window():
    waiting = armed("awaiting_answer")
    assert apply(waiting, "code_window_elapsed") is waiting


def test_answer_window_before_the_code_does_not_end_the_call():
    calling = armed("calling")
    assert apply(calling, "answer_window_elapsed") is calling


def test_a_wrong_one_time_code_does_not_lock_the_static_code():
    done = apply(
        case(state="calling", code_channel="one_time", has_app=True, static_locked=False),
        "code_rejected",
    )
    assert done["result"] == "wrong"
    assert done["static_locked"] is False


def test_keypad_yes_on_an_established_number_is_green():
    done = apply(armed("awaiting_answer", number_recent=False), "answer_yes")
    assert done["state"] == "confirmed"
    assert done["result"] == "sent"
    assert done["answered_via"] == "call"


def test_first_terminal_answer_wins():
    red = apply(armed("awaiting_answer"), "answer_no")
    assert red["result"] == "not_sent"
    assert apply(red, "push_answered_yes") is red
    green = apply(armed("calling"), "push_answered_yes")
    assert green["result"] == "sent"
    assert apply(green, "answer_yes") is green
    yellow = apply(armed("calling"), "code_window_elapsed")
    assert yellow["result"] == "timeout"
    assert apply(yellow, "push_answered_yes") is yellow
    assert apply(yellow, "answer_no") is yellow


def test_apply_does_not_mutate_the_input_and_keeps_extra_keys():
    before = case(
        has_app=True,
        has_push_token=False,
        has_opted_in_phone=True,
        case_id="c1",
    )
    snapshot = dict(before)
    after = apply(before, "start")
    assert before == snapshot
    assert after is not before
    assert after["case_id"] == "c1"
    assert after["state"] == "calling"
    assert after["code_channel"] == "one_time"


def test_inbound_caller_id_is_not_evidence():
    before = case(has_app=True, has_push_token=True, has_opted_in_phone=True)
    with pytest.raises(ValueError):
        apply(before, "caller_id")
    assert before["state"] == "opened"
    assert before["result"] is None


def test_event_must_be_a_string():
    before = case()
    with pytest.raises(TypeError):
        apply(before, None)
    assert before["result"] is None


def test_app_child_who_misses_the_push_can_answer_on_the_one_time_code():
    current = case(
        has_app=True,
        has_push_token=True,
        has_opted_in_phone=True,
        number_recent=False,
    )
    current = apply(current, "start")
    assert current["state"] == "waiting_push"
    assert current["code_channel"] is None
    current = apply(current, "push_window_elapsed")
    assert current["state"] == "calling"
    assert current["code_channel"] == "one_time"
    assert apply(current, "call_accepted") is current
    current = apply(current, "code_accepted")
    assert current["state"] == "awaiting_answer"
    current = apply(current, "answer_yes")
    assert current["state"] == "confirmed"
    assert current["result"] == "sent"
    assert current["answered_via"] == "call"


def test_star_then_keypad_no_is_a_scam():
    current = case(
        has_app=True,
        has_push_token=False,
        has_opted_in_phone=True,
        number_recent=True,
    )
    current = apply(current, "start")
    assert current["code_channel"] == "one_time"
    current = apply(current, "use_static_code")
    assert current["state"] == "calling"
    assert current["code_channel"] == "static"
    current = apply(current, "code_accepted")
    current = apply(current, "answer_no")
    assert current["state"] == "scam"
    assert current["result"] == "not_sent"
    assert current["answered_via"] == "call"


def test_no_app_yes_on_a_new_number_stays_yellow():
    current = apply(
        case(has_app=False, has_push_token=False, has_opted_in_phone=True, number_recent=True),
        "start",
    )
    assert current["state"] == "calling"
    assert current["code_channel"] == "static"
    current = apply(current, "code_accepted")
    current = apply(current, "answer_yes")
    assert current["state"] == "not_confirmed"
    assert current["result"] == "number_recent"
    assert apply(current, "answer_no") is current
