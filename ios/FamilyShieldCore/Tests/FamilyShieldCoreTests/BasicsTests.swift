import XCTest
@testable import FamilyShieldCore

final class BasicsTests: XCTestCase {
    func testSHA256MatchesKnownVectors() {
        XCTAssertEqual(
            Nonces.sha256Hex(""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        XCTAssertEqual(
            Nonces.sha256Hex("abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        )
        XCTAssertEqual(
            Nonces.sha256Hex("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"),
            "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"
        )
    }

    func testLocaleIsKoreanOnlyForKorean() {
        XCTAssertEqual(AppLocale.resolve(Locale(identifier: "ko_KR")), .ko)
        XCTAssertEqual(AppLocale.resolve(Locale(identifier: "en_US")), .en)
        XCTAssertEqual(AppLocale.resolve(Locale(identifier: "ja_JP")), .en)
    }

    func testPhoneAcceptsNanpAndKoreaAndRejectsOthers() {
        XCTAssertEqual(PhoneInput.parse("+1 (555) 123-4567"), .valid(e164: "+15551234567"))
        XCTAssertEqual(PhoneInput.parse("+82 010-1234-5678"), .valid(e164: "+821012345678"))
        XCTAssertEqual(PhoneInput.parse("+44 20 7946 0958"), .unsupportedCountry)
        XCTAssertEqual(PhoneInput.parse("not a number"), .invalid)
        XCTAssertEqual(PhoneInput.parse("+1"), .invalid)
    }

    func testCheckCodeShape() {
        XCTAssertEqual(CodeShape.digits("12-ab-3456", max: 4), "1234")
        XCTAssertTrue(CodeShape.isCheckCode("2580"))
        XCTAssertFalse(CodeShape.isCheckCode("258"))
        XCTAssertFalse(CodeShape.isCheckCode("25801"))
        XCTAssertFalse(CodeShape.isCheckCode("25８0"))
        XCTAssertTrue(CodeShape.checkCodesMatch("2580", "2580"))
        XCTAssertFalse(CodeShape.checkCodesMatch("2580", "2581"))
        XCTAssertTrue(CodeShape.isOTP("123456"))
        XCTAssertFalse(CodeShape.isOTP("12345"))
    }

    func testTimesParseUTCAndOffset() throws {
        let utc = try XCTUnwrap(Times.parse("2026-11-05T07:00:51.061166+00:00"))
        let seoul = try XCTUnwrap(Times.parse("2026-11-05T16:00:51.061166+09:00"))
        XCTAssertEqual(utc.timeIntervalSince1970, seoul.timeIntervalSince1970, accuracy: 0.001)
        XCTAssertNil(Times.parse("not-a-time"))
        let shown = Times.shortTime("2026-11-07T15:42:00+00:00", locale: Locale(identifier: "en_US_POSIX"), timeZone: TimeZone(secondsFromGMT: 0)!)
        XCTAssertTrue(shown.contains("3") && shown.contains("42"), shown)
    }
}
