import Foundation

public enum ShareProblem: String, Codable, Equatable, Sendable {
    case tooLarge = "too_large"
    case empty
    case unsupported
    case unreadable
}

public struct PlannedAudio: Equatable, Sendable {
    public var contentType: String
    public var displayName: String
}

public enum SharePlan: Equatable, Sendable {
    case ignore
    case draft(text: String, audio: PlannedAudio?, problem: ShareProblem?)
}

/// The fields that decide a draft, with no UIKit types.
public struct ShareRequest: Equatable, Sendable {
    public var action: String?
    public var mime: String?
    public var text: String?
    public var hasStream: Bool
    public var displayName: String?
    public var declaredSize: Int64?

    public init(action: String?, mime: String?, text: String?, hasStream: Bool, displayName: String?, declaredSize: Int64?) {
        self.action = action
        self.mime = mime
        self.text = text
        self.hasStream = hasStream
        self.displayName = displayName
        self.declaredSize = declaredSize
    }
}

/// Same marker the Android `ACTION_SEND` uses, so one function decides both platforms.
public let shareSendAction = "android.intent.action.SEND"

/// Decides what a share becomes. Text is a text draft. Audio is planned only
/// when the type (or a known extension) is a voice note and the reported size
/// is within the limit. Sharing never uploads. The parent still taps Verify.
public func planShare(_ request: ShareRequest, maxBytes: Int64 = VoiceNotes.maxBytes) -> SharePlan {
    guard request.action == shareSendAction else { return .ignore }
    let text = String((request.text ?? "").prefix(Limits.text))
    let mime = VoiceNotes.baseType(request.mime)
    if mime == "text/plain" {
        return .draft(text: text, audio: nil, problem: nil)
    }
    let namedAudio = request.hasStream && VoiceNotes.contentType(rawMime: request.mime, fileName: request.displayName) != nil
    let typedAudio = mime != nil && (mime!.hasPrefix("audio/") || mime == "application/ogg")
    if !namedAudio && !typedAudio {
        if mime == nil && !text.isEmpty && !request.hasStream {
            return .draft(text: text, audio: nil, problem: nil)
        }
        return .draft(text: text, audio: nil, problem: .unsupported)
    }
    if !request.hasStream {
        return .draft(text: text, audio: nil, problem: .unsupported)
    }
    guard let contentType = VoiceNotes.contentType(rawMime: request.mime, fileName: request.displayName) else {
        return .draft(text: text, audio: nil, problem: .unsupported)
    }
    if request.declaredSize == 0 {
        return .draft(text: text, audio: nil, problem: .empty)
    }
    if let size = request.declaredSize, size > maxBytes {
        return .draft(text: text, audio: nil, problem: .tooLarge)
    }
    let name = request.displayName?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
        ?? "voice-note.\(VoiceNotes.suffix(contentType))"
    return .draft(text: text, audio: PlannedAudio(contentType: contentType, displayName: name), problem: nil)
}

public struct StoredAudio: Equatable, Sendable {
    public var fileURL: URL
    public var displayName: String
    public var contentType: String
    public var sizeBytes: Int64
}

public enum ShareOutcome: Equatable, Sendable {
    case ignore
    case draft(text: String, audio: StoredAudio?, problem: ShareProblem?)
}

public enum ShareDrafts {
    public static let fileName = "pending-share.json"

    /// Copies one share into `draftsDirectory`. Text does not create a file.
    /// A voice note is copied locally. Nothing is uploaded.
    public static func receive(
        request: ShareRequest,
        bytes: Data?,
        draftsDirectory: URL,
        maxBytes: Int64 = VoiceNotes.maxBytes
    ) -> ShareOutcome {
        let plan = planShare(request, maxBytes: maxBytes)
        guard case .draft(let text, let wanted, let problem) = plan else { return .ignore }
        guard let wanted else {
            if problem == nil { wipe(draftsDirectory) }
            return .draft(text: text, audio: nil, problem: problem)
        }
        guard let bytes else {
            return .draft(text: text, audio: nil, problem: .unreadable)
        }
        let dest = draftsDirectory.appendingPathComponent("voice-\(UUID().uuidString).\(VoiceNotes.suffix(wanted.contentType))")
        switch VoiceNotes.copyCapped(bytes, to: dest, limit: maxBytes) {
        case .ok(let count):
            deleteExcept(dest, in: draftsDirectory)
            let stored = StoredAudio(
                fileURL: dest,
                displayName: VoiceNotes.displayLabel(fileName: wanted.displayName, contentType: wanted.contentType),
                contentType: wanted.contentType,
                sizeBytes: count
            )
            return .draft(text: text, audio: stored, problem: nil)
        case .empty:
            return .draft(text: text, audio: nil, problem: .empty)
        case .tooLarge:
            return .draft(text: text, audio: nil, problem: .tooLarge)
        case .unreadable:
            return .draft(text: text, audio: nil, problem: .unreadable)
        }
    }

    public static func writeMarker(_ outcome: ShareOutcome, directory: URL) throws {
        guard case .draft(let text, let audio, let problem) = outcome else { return }
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let marker = ShareMarker(
            text: text,
            audioFile: audio?.fileURL.lastPathComponent,
            contentType: audio?.contentType,
            displayName: audio?.displayName,
            sizeBytes: audio?.sizeBytes,
            problem: problem?.rawValue
        )
        let data = try JSONEncoder().encode(marker)
        try data.write(to: directory.appendingPathComponent(fileName), options: .atomic)
    }

    public static func readMarker(directory: URL) -> ShareMarker? {
        let url = directory.appendingPathComponent(fileName)
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(ShareMarker.self, from: data)
    }

    public static func wipe(_ directory: URL) {
        guard let items = try? FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil) else { return }
        for item in items { try? FileManager.default.removeItem(at: item) }
    }

    private static func deleteExcept(_ keep: URL, in directory: URL) {
        guard let items = try? FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil) else { return }
        for item in items where item.lastPathComponent != keep.lastPathComponent {
            try? FileManager.default.removeItem(at: item)
        }
    }
}

public struct ShareMarker: Codable, Equatable, Sendable {
    public var text: String
    public var audioFile: String?
    public var contentType: String?
    public var displayName: String?
    public var sizeBytes: Int64?
    public var problem: String?
}

public enum AppGroupID {
    /// Placeholder. Create this App Group on the Apple Developer account and
    /// keep the id in both entitlements. It is not a secret.
    public static let identifier = "group.com.familyshield.app"
    public static let urlScheme = "familyshield"
    public static let shareHost = "share"
}

private extension String {
    var nonEmpty: String? { isEmpty ? nil : self }
}
