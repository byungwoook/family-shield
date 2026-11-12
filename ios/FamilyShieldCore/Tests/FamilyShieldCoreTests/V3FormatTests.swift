import XCTest
@testable import FamilyShieldCore

final class V3FormatTests: XCTestCase {
    func testSixtyEightSecondsIsOneMinuteEight() {
        let now = Date(timeIntervalSince1970: 1_700_000_000)
        let deadline = now.addingTimeInterval(68)
        let remaining = V3Format.remainingSeconds(deadline: deadline, now: now)
        XCTAssertEqual(remaining, 68)
        XCTAssertEqual(V3Format.clock(remaining ?? 0), "01:08")
        XCTAssertEqual(V3Format.currentSegment(remainingSeconds: remaining ?? 0), 7)
        XCTAssertEqual(V3Format.currentSegment(remainingSeconds: 0), -1)
    }

    func testSubjectParticleFollowsHangulBatchim() {
        XCTAssertEqual(V3Format.subjectParticle("지우"), "가")
        XCTAssertEqual(V3Format.subjectParticle("민준"), "이")
        XCTAssertEqual(V3Format.subject("지우", korean: true), "지우가")
        XCTAssertEqual(V3Format.subject("Mina", korean: false), "Mina")
    }
}
