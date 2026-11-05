"""The allow page for a child with no app. Milestone 16.

Server-rendered HTML, no JavaScript, no external requests. The language
follows the number, like the call: `+82` Korean, otherwise English. Every
page is sent with `Cache-Control: no-store`, `Referrer-Policy: no-referrer`,
`X-Robots-Tag: noindex`, and a CSP that allows only inline style and forms
posting back here.

The check code is typed once into a password field and never rendered
back, on success or on error. The parent never sees this page's input.
A GET never changes anything, so a link preview cannot use up the link.
"""

from html import escape

PAGE_HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Robots-Tag": "noindex, nofollow",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
        "base-uri 'none'; frame-ancestors 'none'"
    ),
}

_STYLE = """
body{margin:0;font:17px/1.5 -apple-system,system-ui,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;
background:#f6f7f9;color:#14181f}
main{max-width:30rem;margin:0 auto;padding:1.5rem 1rem 3rem}
h1{font-size:1.4rem;margin:0 0 1rem}
p{margin:0 0 1rem}
.card{background:#fff;border-radius:14px;padding:1.25rem;box-shadow:0 1px 3px rgba(0,0,0,.08)}
label{display:block;font-weight:600;margin:1rem 0 .35rem}
input{box-sizing:border-box;width:100%;font-size:1.3rem;padding:.6rem .75rem;border:1px solid #c6ccd6;
border-radius:10px;letter-spacing:.2em}
button{margin-top:1.25rem;width:100%;font-size:1.05rem;font-weight:600;padding:.85rem;border:0;
border-radius:10px;background:#0b6bcb;color:#fff}
.note{color:#4a5363;font-size:.95rem}
.error{background:#fdecec;color:#8a1c1c;border-radius:10px;padding:.75rem;margin-bottom:1rem}
@media (prefers-color-scheme:dark){body{background:#0f1217;color:#e8ebf0}.card{background:#191e26;
box-shadow:none}input{background:#0f1217;color:#e8ebf0;border-color:#3a4250}.note{color:#a8b0bd}
.error{background:#3a1717;color:#ffd5d5}}
"""

TEXT = {
    "en": {
        "title": "Family Shield",
        "intro": "Your family added this phone number to Family Shield for {name}.",
        "what": (
            "If someone ever sends your family a message that asks for money in your name, "
            "Family Shield may call this number. The call asks for a four-digit check code that "
            "only you know, then whether you sent that message."
        ),
        "allow": "Allow calls and text me a code",
        "not_me": "If this isn't you, close this page. Nothing happens unless you continue.",
        "sent": "We texted a 6-digit code to the number ending {last4}.",
        "otp": "Code from the text",
        "code": "Choose a 4-digit check code",
        "again": "Type the check code again",
        "code_note": (
            "Don't reuse a PIN you use anywhere else. Your family will not see this code, "
            "and the call will never read it back."
        ),
        "save": "Save",
        "done_title": "You're set",
        "done": (
            "Family Shield will call this number only when your family asks it to check a message. "
            "Keep your check code to yourself."
        ),
        "reset_done": "Your new check code is saved. The old one no longer works.",
        "expired": "This link has expired or was already used. Ask your family to send a new one.",
        "wrong_otp": "That code from the text didn't match. Try again.",
        "otp_dead": "That code from the text has expired. Go back to the link and ask for a new one.",
        "bad_code": "The check code must be 4 digits, typed the same way twice.",
        "limited": "Too many codes were sent today. Try again tomorrow.",
        "sms_failed": "We couldn't send the text. Try again in a minute.",
    },
    "ko": {
        "title": "패밀리 쉴드",
        "intro": "가족이 {name}님의 이 전화번호를 패밀리 쉴드에 등록했습니다.",
        "what": (
            "누군가 회원님인 척하며 가족에게 돈을 요구하는 메시지를 보내면, 패밀리 쉴드가 이 번호로 "
            "전화할 수 있습니다. 전화에서는 회원님만 아는 네 자리 확인 번호를 먼저 묻고, 그 메시지를 "
            "직접 보냈는지 묻습니다."
        ),
        "allow": "전화 허용하고 인증번호 받기",
        "not_me": "본인이 아니라면 이 페이지를 닫으세요. 계속하지 않으면 아무 일도 일어나지 않습니다.",
        "sent": "끝자리가 {last4}인 번호로 6자리 인증번호를 보냈습니다.",
        "otp": "문자로 받은 인증번호",
        "code": "네 자리 확인 번호 정하기",
        "again": "확인 번호 한 번 더 입력",
        "code_note": (
            "다른 곳에서 쓰는 비밀번호는 피해 주세요. 가족은 이 번호를 볼 수 없고, 전화에서도 "
            "다시 읽어 주지 않습니다."
        ),
        "save": "저장",
        "done_title": "설정이 끝났습니다",
        "done": (
            "패밀리 쉴드는 가족이 메시지 확인을 요청할 때만 이 번호로 전화합니다. "
            "확인 번호는 혼자만 알고 계세요."
        ),
        "reset_done": "새 확인 번호를 저장했습니다. 이전 번호는 더 이상 쓸 수 없습니다.",
        "expired": "만료됐거나 이미 사용한 링크입니다. 가족에게 새 링크를 보내 달라고 하세요.",
        "wrong_otp": "문자로 받은 인증번호가 맞지 않습니다. 다시 입력해 주세요.",
        "otp_dead": "인증번호가 만료됐습니다. 링크로 돌아가 새 인증번호를 받아 주세요.",
        "bad_code": "확인 번호는 네 자리 숫자로, 두 번 똑같이 입력해 주세요.",
        "limited": "오늘 보낼 수 있는 인증번호를 모두 보냈습니다. 내일 다시 시도해 주세요.",
        "sms_failed": "문자를 보내지 못했습니다. 잠시 후 다시 시도해 주세요.",
    },
}


def page_language(phone_e164: str | None) -> str:
    return "ko" if isinstance(phone_e164, str) and phone_e164.startswith("+82") else "en"


def allow_sms(phone_e164: str, url: str) -> str:
    """The SMS with the link. No family name (parent-typed text), no code."""
    if page_language(phone_e164) == "ko":
        return f"[패밀리 쉴드] 가족이 이 번호를 등록했습니다. 허용하고 확인 번호를 정하려면: {url}"
    return f"Family Shield: your family added this number. To allow it and set your check code: {url}"


def _page(language: str, title: str, body: str) -> str:
    return (
        f'<!doctype html><html lang="{language}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow">'
        f"<title>{escape(title)}</title><style>{_STYLE}</style></head>"
        f'<body><main><h1>{escape(title)}</h1><div class="card">{body}</div></main></body></html>'
    )


def landing(language: str, *, name: str, action: str) -> str:
    t = TEXT[language]
    body = (
        f"<p>{escape(t['intro'].format(name=name))}</p>"
        f"<p>{escape(t['what'])}</p>"
        f'<form method="post" action="{escape(action)}"><button type="submit">{escape(t["allow"])}</button></form>'
        f'<p class="note" style="margin-top:1rem">{escape(t["not_me"])}</p>'
    )
    return _page(language, t["title"], body)


def code_form(language: str, *, last4: str, action: str, error: str | None = None) -> str:
    t = TEXT[language]
    notice = f'<p class="error" role="alert">{escape(t[error])}</p>' if error else ""
    body = (
        f"{notice}<p>{escape(t['sent'].format(last4=last4))}</p>"
        f'<form method="post" action="{escape(action)}" autocomplete="off">'
        f'<label for="otp">{escape(t["otp"])}</label>'
        '<input id="otp" name="otp" inputmode="numeric" autocomplete="one-time-code" '
        'pattern="[0-9]{6}" maxlength="6" required>'
        f'<label for="code">{escape(t["code"])}</label>'
        '<input id="code" name="code" type="password" inputmode="numeric" pattern="[0-9]{4}" '
        'maxlength="4" autocomplete="new-password" required>'
        f'<label for="again">{escape(t["again"])}</label>'
        '<input id="again" name="again" type="password" inputmode="numeric" pattern="[0-9]{4}" '
        'maxlength="4" autocomplete="new-password" required>'
        f'<p class="note" style="margin-top:1rem">{escape(t["code_note"])}</p>'
        f'<button type="submit">{escape(t["save"])}</button></form>'
    )
    return _page(language, t["title"], body)


def done(language: str, *, reset: bool) -> str:
    t = TEXT[language]
    return _page(language, t["done_title"], f"<p>{escape(t['reset_done' if reset else 'done'])}</p>")


def message(language: str, key: str) -> str:
    t = TEXT[language]
    return _page(language, t["title"], f'<p class="error" role="alert">{escape(t[key])}</p>')
