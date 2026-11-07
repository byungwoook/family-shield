import XCTest
@testable import FamilyShieldCore

final class OutboundIdentificationTests: XCTestCase {
    private let ours = OutboundIdentification.placeholderE164
    private let child = "+821012345678"

    func testTheDirectoryContainsExactlyTheConfiguredNumber() {
        let entries = OutboundIdentification.entries(configured: ours)
        XCTAssertEqual(entries.count, 1)
        XCTAssertEqual(entries[0].phoneNumber, 15_555_550_100)
        XCTAssertEqual(entries[0].label, "Family Shield")
        XCTAssertNotEqual(entries[0].label.lowercased(), "genuine")
        XCTAssertFalse(entries.contains { $0.phoneNumber == 82_101_234_5678 })
    }

    func testASecondNumberIsRefused() {
        // The directory is the one configured outbound id. A child number beside it,
        // or any second number, is not an entry.
        XCTAssertTrue(OutboundIdentification.entries(configured: "\(ours),\(child)").isEmpty)
        XCTAssertTrue(OutboundIdentification.entries(configured: "\(ours) \(child)").isEmpty)
        XCTAssertTrue(OutboundIdentification.entries(configured: "").isEmpty)
        XCTAssertTrue(OutboundIdentification.entries(configured: "not-a-number").isEmpty)
        XCTAssertTrue(OutboundIdentification.entries(configured: "+0123").isEmpty)
        let labeled = Set(OutboundIdentification.entries(configured: ours).map(\.phoneNumber))
        XCTAssertFalse(labeled.contains(82_101_234_5678))
    }

    func testOurCallIsAnnouncedAndEveryCallIsAllowedToRing() {
        let oursPlan = OutboundIdentification.plan(incoming: ours, configured: ours)
        XCTAssertTrue(oursPlan.announceFamilyShield)
        XCTAssertFalse(oursPlan.disallowCall)
        XCTAssertFalse(oursPlan.rejectCall)
        XCTAssertFalse(oursPlan.silenceCall)

        let tel = OutboundIdentification.plan(incoming: "tel:+15555550100", configured: ours)
        XCTAssertTrue(tel.announceFamilyShield)
        XCTAssertFalse(tel.silenceCall)

        let childPlan = OutboundIdentification.plan(incoming: child, configured: ours)
        XCTAssertFalse(childPlan.announceFamilyShield)
        XCTAssertFalse(childPlan.disallowCall)
        XCTAssertFalse(childPlan.rejectCall)
        XCTAssertFalse(childPlan.silenceCall)

        let neighbor = OutboundIdentification.plan(incoming: "+15555550101", configured: ours)
        XCTAssertFalse(neighbor.announceFamilyShield)
        XCTAssertFalse(neighbor.silenceCall)

        let missing = OutboundIdentification.plan(incoming: nil, configured: ours)
        XCTAssertFalse(missing.announceFamilyShield)
        XCTAssertFalse(missing.silenceCall)
        XCTAssertFalse(OutboundIdentification.plan(incoming: ours, configured: "").announceFamilyShield)
    }

    func testTheExtensionIdentifiesOneNumberAndDoesNotBlock() throws {
        let plist = try String(contentsOf: iosRoot().appendingPathComponent("CallDirectory/Info.plist"), encoding: .utf8)
        XCTAssertTrue(plist.contains("com.apple.callkit.call-directory"))
        XCTAssertTrue(plist.contains("phoneNumberIdentification"))
        XCTAssertFalse(plist.contains("phoneNumberBlocking"))
        XCTAssertTrue(plist.contains("$(FS_OUTBOUND_CALLER_ID)"))
        XCTAssertTrue(plist.contains("CallDirectoryHandler"))
        XCTAssertFalse(plist.contains(child))

        let project = try String(contentsOf: iosRoot().appendingPathComponent("project.yml"), encoding: .utf8)
        XCTAssertTrue(project.contains("com.familyshield.app.calldirectory"))
        XCTAssertTrue(project.contains("FS_OUTBOUND_CALLER_ID: \"+15555550100\""))

        let handler = try String(contentsOf: iosRoot().appendingPathComponent("CallDirectory/CallDirectoryHandler.swift"), encoding: .utf8)
        XCTAssertTrue(handler.contains("addIdentificationEntry"))
        XCTAssertFalse(handler.contains("addBlockingEntry"))
        XCTAssertFalse(handler.lowercased().contains("verified"))
        XCTAssertTrue(handler.contains("completeRequest"))
    }

    func testOutboundCopyDoesNotGradeTheCaller() {
        let body = CopyCatalog.text(.outboundLabelBody, .en)
        XCTAssertTrue(body.hasPrefix("Optional."))
        XCTAssertTrue(body.contains("check code works without this"))
        XCTAssertFalse(body.lowercased().contains("verified"))
        XCTAssertEqual(CopyCatalog.text(.callerLabelBody, .en), "Family Shield is calling for your family.")
        XCTAssertFalse(CopyCatalog.text(.outboundLabelBody, .ko).isEmpty)
        XCTAssertFalse(CopyCatalog.text(.callerLabelBody, .ko).lowercased().contains("verified"))
    }

    func testLabelSourcesDoNotNameATrustVerdict() throws {
        let files = [
            "FamilyShieldCore/Sources/FamilyShieldCore/OutboundIdentification.swift",
            "CallDirectory/CallDirectoryHandler.swift",
            "App/Sources/CallDirectoryLink.swift",
        ]
        for relative in files {
            let text = try String(contentsOf: iosRoot().appendingPathComponent(relative), encoding: .utf8)
            XCTAssertFalse(text.lowercased().contains("verified"), relative)
        }
    }

    private func iosRoot() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
    }
}
