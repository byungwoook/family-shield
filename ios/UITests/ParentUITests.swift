import XCTest

final class ParentUITests: XCTestCase {
    func testEmptyFamily() {
        let app = launch("emptyFamily")
        XCTAssertTrue(app.staticTexts["No children yet"].waitForExistence(timeout: 5))
    }

    func testUnconfirmedChildDisablesVerify() {
        let app = launch("verifyDisabled")
        let button = app.buttons["verify_11111111-1111-1111-1111-111111111111"]
        XCTAssertTrue(button.waitForExistence(timeout: 5))
        XCTAssertFalse(button.isEnabled)
        XCTAssertTrue(app.staticTexts["Minji wants to join. Number ending 0123."].exists)
    }

    func testYellowResult() {
        let app = launch("yellow")
        XCTAssertTrue(app.staticTexts["Not confirmed"].waitForExistence(timeout: 5))
        let body = app.staticTexts["result_body"]
        XCTAssertTrue(body.waitForExistence(timeout: 5))
        XCTAssertTrue(body.label.contains("Don't send money"))
        XCTAssertTrue(body.label.contains("was wrong"))
        XCTAssertFalse(app.staticTexts["family_alert"].exists)
    }

    func testRedResultOffersTheFamilyWarning() {
        let app = launch("red")
        XCTAssertTrue(app.staticTexts["Scam"].waitForExistence(timeout: 5))
        let body = app.staticTexts["result_body"]
        XCTAssertTrue(body.label.contains("Do not send money"))
        let alert = app.staticTexts["family_alert"]
        XCTAssertTrue(alert.waitForExistence(timeout: 5))
        XCTAssertTrue(alert.label.contains("tuition is due tonight"))
        XCTAssertTrue(app.staticTexts["Warn your family"].exists)
    }

    func testNotNowLeavesTheQuestionWithoutAnswering() {
        let app = launch("notNow")
        XCTAssertTrue(app.staticTexts["child_question"].waitForExistence(timeout: 5))
        app.buttons["not_now"].tap()
        XCTAssertTrue(app.staticTexts["still_open"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.staticTexts["child_question"].exists)
    }

    func testResetHidesTheNewCodeUntilFaceID() {
        let app = launch("resetLocked")
        XCTAssertTrue(app.buttons["reset_unlock"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.textFields["check_code"].exists)
        XCTAssertFalse(app.staticTexts["2580"].exists)
    }

    func testSharedDraftIsNotUploadedUntilVerify() {
        let app = launch("shareDraft")
        XCTAssertTrue(app.staticTexts["Nothing is sent until you tap Verify."].waitForExistence(timeout: 5))
        let attached = app.staticTexts["draft_audio"]
        XCTAssertTrue(attached.waitForExistence(timeout: 5))
        XCTAssertTrue(attached.label.contains("voice.m4a"))
        XCTAssertTrue(attached.label.contains("until you tap Verify"))
    }

    func testRedResultInKorean() {
        let app = XCUIApplication()
        app.launchArguments = ["-AppleLanguages", "(ko)", "-AppleLocale", "ko_KR", "--ui-test", "red"]
        app.launch()
        XCTAssertTrue(app.staticTexts["사기"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["result_body"].label.contains("돈을 보내지 말고"))
    }

    private func launch(_ fixture: String) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = ["--ui-test", fixture]
        app.launch()
        return app
    }
}
