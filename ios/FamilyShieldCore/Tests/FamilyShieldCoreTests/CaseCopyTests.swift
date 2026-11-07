import XCTest
@testable import FamilyShieldCore

final class CaseCopyTests: XCTestCase {
    func testVerifyIsEnabledOnlyWhenActiveAndConfirmed() {
        let ready = Member(id: "c", role: "child", status: "active", confirmedAt: "2026-11-07T00:00:00+00:00")
        XCTAssertTrue(MemberRules.canVerify(ready))
        XCTAssertEqual(MemberRules.stage(ready), .ready)
        let pending = Member(id: "c", role: "child", status: "invited", linked: true, phoneLast4: "0123", phoneVerified: true, awaitingConfirm: true)
        XCTAssertFalse(MemberRules.canVerify(pending))
        XCTAssertEqual(MemberRules.stage(pending), .awaitingConfirm)
        let expired = Member(id: "c", role: "child", status: "invited", inviteExpiresAt: "2020-01-01T00:00:00+00:00")
        let now = Times.parse("2026-11-07T00:00:00+00:00")!
        XCTAssertEqual(MemberRules.stage(expired, now: now), .inviteExpired)
        XCTAssertFalse(MemberRules.canReissueInvite(Member(id: "c", role: "child", status: "invited", phoneLast4: "0123", callOnly: true)))
        XCTAssertTrue(MemberRules.hasPendingNumber(Member(id: "c", role: "child", status: "active", pendingPhoneLast4: "9999")))
    }

    func testEveryResultHasCopyAndOnlyColorPicksGreenOrRed() {
        XCTAssertNil(CaseCopy.result(color: .open, result: nil))
        let green = CaseCopy.result(color: .green, result: "sent")
        XCTAssertEqual(green?.body, .resultSent)
        XCTAssertEqual(green?.color, .green)
        let red = CaseCopy.result(color: .red, result: "not_sent")
        XCTAssertEqual(red?.body, .resultNotSent)
        XCTAssertTrue(CaseCopy.offersFamilyAlert(.red))
        XCTAssertFalse(CaseCopy.offersFamilyAlert(.yellow))
        let yellow: [ResultCode: CopyKey] = [
            .wrong: .resultWrong,
            .noAnswer: .resultNoAnswer,
            .noNumber: .resultNoNumber,
            .callFailed: .resultCallFailed,
            .timeout: .resultTimeout,
            .unreachable: .resultUnreachable,
            .codeLocked: .resultCodeLocked,
            .numberRecent: .resultNumberRecent,
        ]
        for (code, key) in yellow {
            XCTAssertEqual(CaseCopy.result(color: .yellow, result: code.rawValue)?.body, key)
        }
        XCTAssertEqual(CaseCopy.result(color: .yellow, result: "sent")?.body, .resultYellowGeneric)
        XCTAssertEqual(CaseCopy.result(color: .yellow, result: nil)?.body, .resultYellowGeneric)
        for code in ResultCode.allCases {
            XCTAssertEqual(ResultCode(rawValue: code.rawValue), code)
        }
    }

    func testEnglishAndKoreanResultSentences() {
        let name = "Minji"
        let green = CopyCatalog.text(.resultSent, .en, name)
        XCTAssertEqual(green, "Minji confirmed they sent it. The request really came from Minji. Talk to Minji directly before sending anything.")
        let red = CopyCatalog.text(.resultNotSent, .en, name)
        XCTAssertEqual(red, "Minji confirmed they did not send this. Do not send money and do not reply to whoever contacted you.")
        let recent = CopyCatalog.text(.resultNumberRecent, .en, name)
        XCTAssertTrue(recent.contains("last 24 hours"))
        XCTAssertTrue(recent.contains("Don't send money"))
        XCTAssertFalse(green.lowercased().contains("go ahead"))
        let ko = CopyCatalog.text(.resultSent, .ko, name)
        XCTAssertTrue(ko.contains("보내기 전에"))
        XCTAssertTrue(CopyCatalog.text(.resultNotSent, .ko, name).contains("돈을 보내지 말고"))
        let pattern = CopyCatalog.text(.patternLineGreen, .en, "payment in gift cards", name)
        XCTAssertTrue(pattern.contains("gift cards, crypto, and wire transfers"))
        XCTAssertFalse(pattern.lowercased().contains("send the money"))
    }

    func testTimelinePatternsAndUnknownColor() {
        let known = [
            "start", "push_answered_yes", "push_answered_no", "push_failed", "push_window_elapsed",
            "call_failed", "call_busy", "call_no_answer", "call_ended_before_code", "call_ended_before_answer",
            "code_window_elapsed", "use_static_code", "code_accepted", "static_code_mismatch",
            "code_did_not_match", "one_time_code_expired", "code_rejected", "answer_yes", "answer_no",
            "answer_unclear", "answer_window_elapsed", "phone_number_changed",
        ]
        for step in known {
            XCTAssertNotEqual(CaseCopy.timelineStep(step), .timelineUnknown, step)
        }
        XCTAssertEqual(CaseCopy.timelineStep("call_accepted"), .timelineUnknown)
        XCTAssertEqual(CaseCopy.patternLabel("gift_card"), .patternGiftCard)
        XCTAssertNil(CaseCopy.patternLabel("none"))
        XCTAssertNil(CaseCopy.patternLabel("not-a-pattern"))
        XCTAssertEqual(CaseCopy.patternLine(.green), .patternLineGreen)
        XCTAssertEqual(CaseCopy.patternLine(.red), .patternLineInfo)
        XCTAssertEqual(CaseColor.of("purple", decidedAt: nil), .open)
        XCTAssertEqual(CaseColor.of("purple", decidedAt: "2026-11-07T00:00:00+00:00"), .yellow)
    }

    func testCopyPlaceholdersMatchAcrossLanguages() {
        let pattern = try! NSRegularExpression(pattern: "%(\\d+)\\$[sd]")
        for key in CopyKey.allCases {
            let en = CopyCatalog.template(key, .en)
            let ko = CopyCatalog.template(key, .ko)
            XCTAssertFalse(en.isEmpty, key.rawValue)
            XCTAssertFalse(ko.isEmpty, key.rawValue)
            XCTAssertEqual(placeholders(en, pattern), placeholders(ko, pattern), key.rawValue)
        }
    }

    func testParentFixturesCoverTheMilestoneScreens() {
        let now = Times.parse("2026-11-07T00:00:00+00:00")!
        let empty = ParentFixtures.home(.emptyFamily, locale: .en, now: now)!
        XCTAssertTrue(empty.isEmpty)
        XCTAssertEqual(empty.familyName, "Lee")
        let pending = ParentFixtures.home(.verifyDisabled, locale: .en, now: now)!
        XCTAssertEqual(pending.children.count, 1)
        XCTAssertFalse(pending.children[0].canVerify)
        XCTAssertNotNil(pending.children[0].joinRequest)
        let yellow = CasePresenter.present(
            ParentFixtures.caseItem(.yellow)!,
            locale: .en,
            formattingLocale: Locale(identifier: "en_US_POSIX"),
            timeZone: TimeZone(secondsFromGMT: 0)!
        )
        XCTAssertEqual(yellow.color, .yellow)
        XCTAssertEqual(yellow.title, "Not confirmed")
        XCTAssertTrue(yellow.body.contains("was wrong"))
        XCTAssertTrue(yellow.body.contains("Don't send money"))
        XCTAssertNil(yellow.familyAlert)
        XCTAssertEqual(yellow.dontSend, nil)
        let red = CasePresenter.present(
            ParentFixtures.caseItem(.red)!,
            locale: .ko,
            formattingLocale: Locale(identifier: "ko_KR"),
            timeZone: TimeZone(secondsFromGMT: 0)!
        )
        XCTAssertEqual(red.color, .red)
        XCTAssertEqual(red.title, "사기")
        XCTAssertTrue(red.body.contains("돈을 보내지 말고"))
        XCTAssertTrue(red.familyAlert?.contains("tuition is due tonight") == true)
        XCTAssertNotNil(red.patternLine)
    }

    func testSessionRoute() {
        XCTAssertEqual(SessionRoute.destination(for: Me(userId: "u")), .needsFamily)
        let parent = Me(userId: "u", memberships: [
            Membership(memberId: "m", familyId: "f", familyName: "Lee", role: "parent", status: "active"),
        ])
        XCTAssertEqual(SessionRoute.destination(for: parent), .parent(familyId: "f", familyName: "Lee"))
        let child = Me(userId: "u", memberships: [
            Membership(memberId: "m", familyId: "f", familyName: "Lee", role: "child", status: "invited", displayName: "Minji"),
        ])
        XCTAssertEqual(
            SessionRoute.destination(for: child),
            .child(ChildDestination(memberId: "m", familyId: "f", familyName: "Lee", status: "invited", displayName: "Minji"))
        )
    }

    func testPollingStopsWhenDecidedAndOn401() {
        let open = ParentCase(id: "c", state: "calling", color: "open")
        XCTAssertEqual(CasePolling.outcome(.success(open)), .open(open))
        let yellow = ParentCase(id: "c", state: "not_confirmed", result: "wrong", color: "yellow", decidedAt: "2026-11-07T00:00:00+00:00")
        XCTAssertEqual(CasePolling.outcome(.success(yellow)), .decided(yellow))
        XCTAssertEqual(CasePolling.outcome(.failure(.http(status: 401, code: "unauthorized"))), .unauthorized)
        XCTAssertEqual(CasePolling.outcome(.failure(.network)), .failedKeepWaiting)
        XCTAssertEqual(ErrorCopy.key(for: .http(status: 429, code: "rate_limited")), .errorRateLimited)
        XCTAssertEqual(ErrorCopy.key(for: .http(status: 400, code: "member_not_callable")), .errorMemberNotCallable)
        XCTAssertEqual(ErrorCopy.key(for: .http(status: 500, code: "unavailable")), .errorServer)
    }

    private func placeholders(_ text: String, _ pattern: NSRegularExpression) -> [String] {
        let range = NSRange(text.startIndex..., in: text)
        return pattern.matches(in: text, range: range).map {
            String(text[Range($0.range, in: text)!])
        }.sorted()
    }
}
