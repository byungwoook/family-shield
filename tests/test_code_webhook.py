"""Digit folding for the hackathon webhook and the product keypad.

`services.code_webhook._digits` is the one folding function. The product
API calls it and does not call `_yes_no`. These tests are the copy the
milestone asks for, so a change to folding fails here and in the API
tests together. `make_app` stays the hackathon webhook.
"""

import services.code_webhook as webhook
from services.code_webhook import _digits, _yes_no, make_app


def test_ascii_digits_pass_through():
    assert _digits("2580") == "2580"
    assert _digits("1") == "1"
    assert _digits("") == ""


def test_devanagari_digits_fold_to_ascii():
    assert _digits("२५८०") == "2580"
    assert _digits("५") == "5"


def test_fullwidth_digits_fold_to_ascii():
    assert _digits("２５８０") == "2580"
    assert _digits("１") == "1"


def test_arabic_indic_digits_fold_to_ascii():
    assert _digits("١٢٣٤") == "1234"


def test_letters_star_and_words_contribute_no_digits():
    assert _digits("*") == ""
    assert _digits("yes") == ""
    assert _digits("yeah") == ""
    assert _digits("nope") == ""
    assert _digits("code 25-80") == "2580"


def test_yes_no_still_maps_spoken_answers_for_the_hackathon_webhook():
    # The product call does not use this. The hackathon agent still does.
    assert _yes_no("yes") == "yes"
    assert _yes_no("yeah") == "yes"
    assert _yes_no("1") == "yes"
    assert _yes_no("nope") == "no"
    assert _yes_no("2") == "no"
    assert _yes_no("not sure") == ""
    assert _yes_no("no answer") == ""


def test_make_app_still_folds_digits_and_spoken_answers(monkeypatch):
    monkeypatch.setattr(webhook, "CODE_WEBHOOK_SECRET", "test-secret")
    seen = {}

    def on_code(_case_id, digits):
        seen["digits"] = digits
        return "ask"

    def on_answer(_case_id, answer):
        seen["answer"] = answer
        return "recorded"

    from fastapi.testclient import TestClient

    client = TestClient(make_app(on_code, on_answer))
    code = client.post(
        "/tools/verify_code",
        json={"case_id": "c", "code": "२५८०"},
        headers={"Authorization": "Bearer test-secret"},
    )
    answer = client.post(
        "/tools/confirm_sent",
        json={"case_id": "c", "answer": "yeah"},
        headers={"Authorization": "Bearer test-secret"},
    )
    assert code.status_code == 200
    assert code.json() == {"result": "ask"}
    assert seen["digits"] == "2580"
    assert answer.status_code == 200
    assert answer.json() == {"result": "recorded"}
    assert seen["answer"] == "yes"
    assert "२५८०" not in code.text
