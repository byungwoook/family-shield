import XCTest
@testable import FamilyShieldCore

final class ChildRulesTests: XCTestCase {
    private let caseId = "22222222-2222-2222-2222-222222222222"

    func testActiveChildSkipsThePhoneStep() {
        XCTAssertEqual(ChildRules.step(status: "active", phoneVerified: false, checkCodeSet: false), .checkCode)
        XCTAssertEqual(ChildRules.step(status: "invited", phoneVerified: false, checkCodeSet: false), .phone)
        XCTAssertEqual(ChildRules.step(status: "invited", phoneVerified: true, checkCodeSet: true), .waiting)
        XCTAssertEqual(ChildRules.step(status: "active", phoneVerified: true, checkCodeSet: true), .home)
    }

    func testNotNowPostsNothingAndLeavesTheCaseOpen() {
        var state = ChildPrompt(prompt: true, caseState: "waiting_push", revealedCode: "123456", pending: .answerYes)
        let (next, effect) = ChildDecisions.notNow(state)
        XCTAssertEqual(effect, .none)
        XCTAssertFalse(next.prompt)
        XCTAssertNil(next.revealedCode)
        XCTAssertNil(next.pending)
        XCTAssertEqual(next.caseState, "waiting_push")
        _ = state
    }

    func testAnswerAndCodeRequireASuccessfulBiometric() {
        let calling = ChildPrompt(prompt: true, caseState: "calling")
        let (failed, failedEffect) = ChildDecisions.biometric(false, ChildDecisions.ask(.answerNo, calling)!)
        XCTAssertEqual(failedEffect, .none)
        XCTAssertNil(failed.revealedCode)
        let (yes, yesEffect) = ChildDecisions.biometric(true, ChildDecisions.ask(.answerYes, calling)!)
        XCTAssertEqual(yesEffect, .postAnswer("yes"))
        XCTAssertNil(yes.revealedCode)
        let (reveal, revealEffect) = ChildDecisions.biometric(true, ChildDecisions.ask(.revealCode, calling)!)
        XCTAssertEqual(revealEffect, .fetchCallCode)
        XCTAssertNil(ChildDecisions.ask(.revealCode, ChildPrompt(prompt: true, caseState: "waiting_push")))
        let shown = ChildDecisions.applyCallCode("654321", fallback: nil, to: calling)
        XCTAssertEqual(shown.revealedCode, "654321")
        let hidden = ChildDecisions.retainCode(shown, newState: "awaiting_answer")
        XCTAssertNil(hidden.revealedCode)
        let fallback = ChildDecisions.applyCallCode(nil, fallback: "static", to: calling)
        XCTAssertTrue(fallback.callFallback)
        XCTAssertNil(fallback.revealedCode)
    }

    func testResetRequiresFaceIDAndDropsTheOldCode() {
        XCTAssertNil(ChildDecisions.resetJSON(first: "1397", second: "1397", unlocked: false))
        XCTAssertNil(ChildDecisions.resetJSON(first: "1397", second: "1398", unlocked: true))
        let old = "2580"
        let body = ChildDecisions.resetJSON(first: "1397", second: "1397", unlocked: true)
        XCTAssertEqual(body, #"{"biometric_ok":true,"code":"1397"}"#)
        XCTAssertFalse(body!.contains(old))
        let (unlocked, effect) = ChildDecisions.biometric(true, ChildPrompt(pending: .resetCode))
        XCTAssertEqual(effect, .none)
        XCTAssertTrue(unlocked.resetUnlocked)
    }

    func testNotificationHasNoCodeAndNoAnswer() {
        let noisy = [
            "kind": "money_request",
            "case_id": caseId,
            "code": "654321",
            "digits": "2580",
            "one_time_code": "111111",
        ]
        let tap = PushAlert.tapInfo(noisy)
        XCTAssertEqual(tap, ["kind": "money_request", "case_id": caseId])
        XCTAssertNil(PushAlert.tapInfo(["kind": "number_change_confirmed", "family_id": caseId, "code": "654321"]))
        for locale in [AppLocale.en, .ko] {
            let body = PushAlert.body(locale)
            XCTAssertFalse(body.contains("654321"))
            XCTAssertNil(body.range(of: #"\d{4,}"#, options: .regularExpression))
        }
        XCTAssertEqual(PushAlert.body(.en), "Family Shield needs you to confirm a request.")
        XCTAssertEqual(PushAlert.body(.ko), "패밀리 쉴드에서 확인이 필요한 요청이 있어요.")
    }

    func testInviteShape() {
        XCTAssertEqual(ChildRules.normalizeInvite("gp9b 8gku-dcvn"), "GP9B8GKUDCVN")
        XCTAssertTrue(ChildRules.inviteLooksValid("23456789ABCD"))
        XCTAssertFalse(ChildRules.inviteLooksValid("23456789ABCO"))
        XCTAssertTrue(ChildRules.isCaseId(caseId))
        XCTAssertFalse(ChildRules.isCaseId("not-a-case"))
    }
}
