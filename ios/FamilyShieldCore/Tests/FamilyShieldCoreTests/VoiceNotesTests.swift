import XCTest
@testable import FamilyShieldCore

final class VoiceNotesTests: XCTestCase {
    func testLimitIsTenMegabytes() {
        XCTAssertEqual(VoiceNotes.maxBytes, 10_485_760)
    }

    func testMessengerFormatsBecomeAudioTypes() {
        let cases: [(String?, String, String?)] = [
            ("audio/mp4", "voice.m4a", "audio/mp4"),
            ("audio/x-m4a", "voice.m4a", "audio/mp4"),
            ("audio/m4a", "voice.m4a", "audio/mp4"),
            ("audio/aac", "voice.aac", "audio/aac"),
            ("audio/mp4a-latm", "voice.aac", "audio/aac"),
            ("audio/ogg", "voice.ogg", "audio/ogg"),
            ("audio/ogg; codecs=opus", "voice.ogg", "audio/ogg"),
            ("audio/ogg; codecs=opus", "voice.opus", "audio/opus"),
            ("audio/opus", "voice.opus", "audio/opus"),
            ("application/ogg", "voice.ogg", "audio/ogg"),
            ("application/ogg", "voice.opus", "audio/opus"),
            ("audio/amr", "voice.amr", "audio/amr"),
            ("audio/amr-wb", "voice.awb", "audio/amr"),
            ("audio/3gpp", "voice.3gp", "audio/3gpp"),
            ("application/octet-stream", "voice.m4a", "audio/mp4"),
            ("application/octet-stream", "voice.opus", "audio/opus"),
            ("application/octet-stream", "memo.caf", "audio/x-caf"),
            ("audio/mpeg", "a.mp3", "audio/mpeg"),
            ("audio/wav", "a.wav", "audio/wav"),
            ("audio/webm", "a.webm", "audio/webm"),
            (nil, "voice.m4a", "audio/mp4"),
            (nil, "clip.mp4", nil),
            ("video/mp4", "clip.mp4", nil),
            ("video/mp4", "voice.m4a", nil),
            ("application/octet-stream", "clip.mp4", nil),
            ("application/octet-stream", "voice.3gp", nil),
            ("image/jpeg", "a.jpg", nil),
            ("text/plain", "a.txt", nil),
        ]
        for (mime, name, expected) in cases {
            XCTAssertEqual(VoiceNotes.contentType(rawMime: mime, fileName: name), expected, "\(mime ?? "nil") \(name)")
        }
    }

    func testUploadNameDropsPathsAndUnsafeCharacters() {
        XCTAssertEqual(VoiceNotes.uploadName(displayName: "voice.m4a", contentType: "audio/mp4"), "voice.m4a")
        XCTAssertEqual(VoiceNotes.uploadName(displayName: "../../etc/passwd.m4a", contentType: "audio/mp4"), "passwd.m4a")
        XCTAssertEqual(VoiceNotes.uploadName(displayName: "엄마 음성.m4a", contentType: "audio/mp4"), "voice-note.m4a")
        XCTAssertEqual(VoiceNotes.uploadName(displayName: nil, contentType: "audio/ogg"), "voice-note.ogg")
        XCTAssertEqual(VoiceNotes.uploadName(displayName: "a\"b\n.m4a", contentType: "audio/mp4"), "ab.m4a")
        XCTAssertEqual(VoiceNotes.displayLabel(fileName: "folder/엄마 음성.m4a", contentType: "audio/mp4"), "엄마 음성.m4a")
    }

    func testCopyStopsAtTheLimit() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let ok = dir.appendingPathComponent("ok.bin")
        XCTAssertEqual(VoiceNotes.copyCapped(Data([1, 2, 3, 4]), to: ok, limit: 4), .ok(4))
        XCTAssertEqual(try Data(contentsOf: ok), Data([1, 2, 3, 4]))
        let big = dir.appendingPathComponent("big.bin")
        XCTAssertEqual(VoiceNotes.copyCapped(Data([1, 2, 3, 4, 5]), to: big, limit: 4), .tooLarge)
        XCTAssertFalse(FileManager.default.fileExists(atPath: big.path))
        let empty = dir.appendingPathComponent("empty.bin")
        XCTAssertEqual(VoiceNotes.copyCapped(Data(), to: empty, limit: 4), .empty)
        XCTAssertFalse(FileManager.default.fileExists(atPath: empty.path))
    }

    func testTextShareDoesNotCreateAFileAndAudioOverTheLimitIsRefused() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        let text = ShareDrafts.receive(
            request: ShareRequest(action: shareSendAction, mime: "text/plain", text: "send money", hasStream: false, displayName: nil, declaredSize: nil),
            bytes: nil,
            draftsDirectory: dir,
            maxBytes: 8
        )
        guard case .draft(let body, nil, nil) = text else { return XCTFail("\(text)") }
        XCTAssertEqual(body, "send money")
        var isDir: ObjCBool = false
        if FileManager.default.fileExists(atPath: dir.path, isDirectory: &isDir) {
            let items = try FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
            XCTAssertTrue(items.isEmpty)
        }

        let ok = ShareDrafts.receive(
            request: ShareRequest(action: shareSendAction, mime: "audio/mp4", text: "caption", hasStream: true, displayName: "voice.m4a", declaredSize: 4),
            bytes: Data([1, 2, 3, 4]),
            draftsDirectory: dir,
            maxBytes: 4
        )
        guard case .draft(_, let audio?, nil) = ok else { return XCTFail("\(ok)") }
        XCTAssertEqual(audio.contentType, "audio/mp4")
        XCTAssertEqual(audio.displayName, "voice.m4a")
        XCTAssertEqual(audio.sizeBytes, 4)
        XCTAssertEqual(try Data(contentsOf: audio.fileURL), Data([1, 2, 3, 4]))

        let rejected = ShareDrafts.receive(
            request: ShareRequest(action: shareSendAction, mime: "audio/mp4", text: "caption", hasStream: true, displayName: "big.m4a", declaredSize: nil),
            bytes: Data([1, 2, 3, 4, 5]),
            draftsDirectory: dir,
            maxBytes: 4
        )
        guard case .draft(_, nil, .tooLarge) = rejected else { return XCTFail("\(rejected)") }
        let left = try FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
        XCTAssertEqual(left.map(\.lastPathComponent), [audio.fileURL.lastPathComponent])
    }

    func testStreamingCopyStopsWithoutReadingPastTheLimit() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let source = dir.appendingPathComponent("source.bin")
        try Data([1, 2, 3, 4, 5]).write(to: source)
        let dest = dir.appendingPathComponent("dest.bin")
        XCTAssertEqual(VoiceNotes.copyCapped(from: source, to: dest, limit: 4), .tooLarge)
        XCTAssertFalse(FileManager.default.fileExists(atPath: dest.path))
        let ok = dir.appendingPathComponent("ok.bin")
        XCTAssertEqual(VoiceNotes.copyCapped(from: source, to: ok, limit: 5), .ok(5))
        XCTAssertEqual(try Data(contentsOf: ok), Data([1, 2, 3, 4, 5]))
    }

    func testDeclaredOversizeIsRefusedBeforeACopy() {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let outcome = ShareDrafts.receive(
            request: ShareRequest(action: shareSendAction, mime: "audio/mp4", text: "", hasStream: true, displayName: "big.m4a", declaredSize: 11),
            bytes: Data([1, 2, 3]),
            draftsDirectory: dir,
            maxBytes: 10
        )
        guard case .draft(_, nil, .tooLarge) = outcome else { return XCTFail("\(outcome)") }
        XCTAssertFalse(FileManager.default.fileExists(atPath: dir.path))
    }

    func testOtherActionsAreIgnored() {
        let plan = planShare(ShareRequest(action: "android.intent.action.MAIN", mime: "text/plain", text: "hi", hasStream: false, displayName: nil, declaredSize: nil))
        XCTAssertEqual(plan, .ignore)
    }
}
