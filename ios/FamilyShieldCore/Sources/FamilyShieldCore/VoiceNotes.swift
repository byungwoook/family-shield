import Foundation

/// Voice-note rules for the share extension and for `POST /v1/cases`.
///
/// The server accepts an audio content type of at most 10 MB (10 485 760 bytes)
/// and requires `Content-Length`. Messengers do not all use the same type.
/// A container that is often a video (`.mp4`, `.webm`, `.3gp`) is accepted
/// only when the sender already called it audio.
public enum VoiceNotes {
    public static let maxBytes: Int64 = 10 * 1024 * 1024

    private static let audioOnlyExtension: [String: String] = [
        "m4a": "audio/mp4",
        "aac": "audio/aac",
        "ogg": "audio/ogg",
        "oga": "audio/ogg",
        "opus": "audio/opus",
        "amr": "audio/amr",
        "awb": "audio/amr",
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "wave": "audio/wav",
        "caf": "audio/x-caf",
        "flac": "audio/flac",
        "gsm": "audio/gsm",
    ]

    public static func baseType(_ rawMime: String?) -> String? {
        let base = rawMime?.split(separator: ";", maxSplits: 1).first.map { $0.trimmingCharacters(in: .whitespaces).lowercased() } ?? ""
        return base.isEmpty ? nil : base
    }

    public static func fileExtension(_ fileName: String?) -> String? {
        let base = fileName?.split(separator: "/").last.map(String.init)?.split(separator: "\\").last.map(String.init)?.trimmingCharacters(in: .whitespaces) ?? ""
        guard let dot = base.lastIndex(of: "."), dot != base.startIndex, base.index(after: dot) != base.endIndex else { return nil }
        let ext = base[base.index(after: dot)...].lowercased()
        guard (1...8).contains(ext.count), ext.allSatisfy({ $0.isLetter || $0.isNumber }) else { return nil }
        return ext
    }

    public static func contentType(rawMime: String?, fileName: String?) -> String? {
        let mime = baseType(rawMime)
        let ext = fileExtension(fileName)
        if let mime, mime.hasPrefix("audio/") { return canonical(mime, ext) }
        if mime == "application/ogg" { return ext == "opus" ? "audio/opus" : "audio/ogg" }
        if mime == nil || mime == "*/*" || mime == "application/octet-stream" || mime == "binary/octet-stream" {
            return ext.flatMap { audioOnlyExtension[$0] }
        }
        if let mime, mime.hasPrefix("application/") { return ext.flatMap { audioOnlyExtension[$0] } }
        return nil
    }

    public static func suffix(_ contentType: String) -> String {
        switch contentType {
        case "audio/mp4": return "m4a"
        case "audio/aac": return "aac"
        case "audio/ogg": return "ogg"
        case "audio/opus": return "opus"
        case "audio/amr": return "amr"
        case "audio/mpeg": return "mp3"
        case "audio/wav": return "wav"
        case "audio/webm": return "webm"
        case "audio/3gpp": return "3gp"
        case "audio/flac": return "flac"
        case "audio/x-caf": return "caf"
        case "audio/gsm": return "gsm"
        default: return "audio"
        }
    }

    public static func displayLabel(fileName: String?, contentType: String) -> String {
        let base = fileName?.split(separator: "/").last.map(String.init)?.split(separator: "\\").last.map(String.init)?.trimmingCharacters(in: .whitespaces) ?? ""
        var cleaned = ""
        for scalar in base.unicodeScalars {
            if scalar == "\"" || scalar == "\r" || scalar == "\n" || scalar.value < 32 { continue }
            cleaned.unicodeScalars.append(scalar)
            if cleaned.count >= 80 { break }
        }
        cleaned = cleaned.trimmingCharacters(in: .whitespaces)
        if cleaned.isEmpty { return "voice-note.\(suffix(contentType))" }
        return cleaned
    }

    public static func uploadName(displayName: String?, contentType: String) -> String {
        let base = displayName?.split(separator: "/").last.map(String.init)?.split(separator: "\\").last.map(String.init)?.trimmingCharacters(in: .whitespaces) ?? ""
        var cleaned = ""
        for character in base {
            let ascii = character.isASCII && (character.isLetter || character.isNumber || character == "." || character == "_" || character == "-")
            if ascii { cleaned.append(character) }
            if cleaned.count >= 80 { break }
        }
        cleaned = cleaned.trimmingCharacters(in: CharacterSet(charactersIn: "."))
        let ext = suffix(contentType)
        if cleaned.isEmpty || cleaned.lowercased() == ext { return "voice-note.\(ext)" }
        if fileExtension(cleaned) == nil { return "\(cleaned).\(ext)" }
        return cleaned
    }

    public enum CopyResult: Equatable {
        case ok(Int64)
        case empty
        case tooLarge
        case unreadable
    }

    /// Copies `source` into `dest` and stops if another byte would pass `limit`.
    /// The source is not read past the limit. Empty, too-large, and unreadable
    /// results delete `dest`.
    public static func copyCapped(from source: URL, to dest: URL, limit: Int64 = maxBytes) -> CopyResult {
        do {
            let input = try FileHandle(forReadingFrom: source)
            defer { try? input.close() }
            try FileManager.default.createDirectory(at: dest.deletingLastPathComponent(), withIntermediateDirectories: true)
            FileManager.default.createFile(atPath: dest.path, contents: nil)
            let output = try FileHandle(forWritingTo: dest)
            defer { try? output.close() }
            var written: Int64 = 0
            while true {
                guard let chunk = try input.read(upToCount: 8192), !chunk.isEmpty else { break }
                if written + Int64(chunk.count) > limit {
                    try? output.close()
                    try? FileManager.default.removeItem(at: dest)
                    return .tooLarge
                }
                try output.write(contentsOf: chunk)
                written += Int64(chunk.count)
            }
            if written == 0 {
                try? FileManager.default.removeItem(at: dest)
                return .empty
            }
            return .ok(written)
        } catch {
            try? FileManager.default.removeItem(at: dest)
            return .unreadable
        }
    }

    /// Copies `bytes` into `dest` and stops if another byte would pass `limit`.
    /// Empty, too-large, and unreadable results delete `dest`.
    public static func copyCapped(_ bytes: Data, to dest: URL, limit: Int64 = maxBytes) -> CopyResult {
        if bytes.isEmpty {
            try? FileManager.default.removeItem(at: dest)
            return .empty
        }
        if Int64(bytes.count) > limit {
            try? FileManager.default.removeItem(at: dest)
            return .tooLarge
        }
        do {
            try FileManager.default.createDirectory(at: dest.deletingLastPathComponent(), withIntermediateDirectories: true)
            try bytes.write(to: dest, options: .atomic)
            return .ok(Int64(bytes.count))
        } catch {
            try? FileManager.default.removeItem(at: dest)
            return .unreadable
        }
    }

    private static func canonical(_ mime: String, _ ext: String?) -> String {
        switch mime {
        case "audio/m4a", "audio/x-m4a", "audio/mp4", "audio/x-mp4": return "audio/mp4"
        case "audio/aac", "audio/x-aac", "audio/mp4a-latm": return "audio/aac"
        case "audio/opus": return "audio/opus"
        case "audio/ogg", "audio/vorbis", "audio/x-ogg": return ext == "opus" ? "audio/opus" : "audio/ogg"
        case "audio/amr", "audio/amr-wb": return "audio/amr"
        case "audio/3gpp", "audio/3gpp2": return "audio/3gpp"
        case "audio/mpeg", "audio/mp3", "audio/mpeg3", "audio/x-mpeg", "audio/x-mp3": return "audio/mpeg"
        case "audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave": return "audio/wav"
        case "audio/webm", "audio/x-webm": return "audio/webm"
        case "audio/flac", "audio/x-flac": return "audio/flac"
        default: return mime
        }
    }
}

private extension Character {
    var isASCII: Bool { unicodeScalars.allSatisfy { $0.isASCII } }
}
