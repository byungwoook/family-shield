import Foundation

public enum Limits {
    public static let name = 200
    public static let phone = 32
    public static let text = 8000
    /// Contract limit for a voice-note part. Sharing uses it in milestone 10.
    public static let audioBytes: Int64 = 10 * 1024 * 1024
}

public enum Nonces {
    /// Lowercase hex SHA-256 of the raw nonce. That hex is the Apple request nonce.
    public static func sha256Hex(_ raw: String) -> String {
        SHA256.hex(Array(raw.utf8))
    }
}

public enum CodeShape {
    public static func digits(_ raw: String, max: Int) -> String {
        String(raw.filter(\.isNumber).prefix(max))
    }

    /// Six ASCII digits, the SMS OTP shape. A miss still counts on the server.
    public static func isOTP(_ code: String) -> Bool {
        code.count == 6 && code.allSatisfy(\.isASCIIDigit)
    }

    /// Exactly four ASCII digits. The parent never sees this value.
    public static func isCheckCode(_ code: String) -> Bool {
        code.count == 4 && code.allSatisfy(\.isASCIIDigit)
    }

    public static func checkCodesMatch(_ first: String, _ second: String) -> Bool {
        isCheckCode(first) && first == second
    }
}

private extension Character {
    var isASCIIDigit: Bool { self >= "0" && self <= "9" }
}

/// What the parent typed as a child's number, checked the way the server checks it.
public enum PhoneInput: Equatable, Sendable {
    case valid(e164: String)
    case invalid
    case unsupportedCountry

    /// Removes spaces, dashes, dots, and brackets. A Korean number written with
    /// its trunk zero after the country code ("+82 010 ...") loses that zero,
    /// because E.164 has none. Only +1 and +82 are supported.
    public static func parse(_ raw: String) -> PhoneInput {
        let dropped = CharacterSet.whitespacesAndNewlines.union(CharacterSet(charactersIn: "().-"))
        var compact = raw.unicodeScalars.filter { !dropped.contains($0) }.map(String.init).joined()
        if compact.hasPrefix("+820") {
            compact = "+82" + compact.dropFirst(4)
        }
        guard let range = compact.range(of: #"^\+[1-9][0-9]{1,14}$"#, options: .regularExpression) else {
            return .invalid
        }
        let e164 = String(compact[range])
        guard e164.hasPrefix("+1") || e164.hasPrefix("+82") else { return .unsupportedCountry }
        return .valid(e164: e164)
    }
}

public enum Times {
    public static func parse(_ iso: String?) -> Date? {
        guard let iso else { return nil }
        let raw = iso.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !raw.isEmpty else { return nil }
        let body: String
        let offset: Int
        if raw.hasSuffix("Z") {
            body = String(raw.dropLast())
            offset = 0
        } else if let sign = raw.lastIndex(where: { $0 == "+" || $0 == "-" }), sign > raw.startIndex {
            body = String(raw[..<sign])
            guard let parsed = zoneOffset(String(raw[sign...])) else { return nil }
            offset = parsed
        } else {
            return nil
        }
        let pieces = body.split(separator: ".", omittingEmptySubsequences: false)
        guard pieces.count == 1 || pieces.count == 2 else { return nil }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        guard let base = formatter.date(from: String(pieces[0])) else { return nil }
        var fraction = 0.0
        if pieces.count == 2 {
            let digits = pieces[1].prefix(9)
            guard !digits.isEmpty, digits.allSatisfy(\.isNumber) else { return nil }
            fraction = (Double(digits) ?? 0) / pow(10, Double(digits.count))
        }
        return base.addingTimeInterval(fraction - Double(offset))
    }

    public static func shortTime(_ iso: String?, locale: Locale, timeZone: TimeZone = .current) -> String {
        guard let date = parse(iso) else { return "" }
        let formatter = DateFormatter()
        formatter.locale = locale
        formatter.timeZone = timeZone
        formatter.timeStyle = .short
        formatter.dateStyle = .none
        return formatter.string(from: date)
    }

    public static func shortDateTime(_ iso: String?, locale: Locale, timeZone: TimeZone = .current) -> String {
        guard let date = parse(iso) else { return "" }
        let formatter = DateFormatter()
        formatter.locale = locale
        formatter.timeZone = timeZone
        formatter.timeStyle = .short
        formatter.dateStyle = .short
        return formatter.string(from: date)
    }

    private static func zoneOffset(_ text: String) -> Int? {
        let pattern = #"^([+-])(\d{2}):?(\d{2})$"#
        guard let match = text.range(of: pattern, options: .regularExpression) else { return nil }
        let value = String(text[match])
        let sign: Int = value.hasPrefix("-") ? -1 : 1
        let digits = value.dropFirst().replacingOccurrences(of: ":", with: "")
        guard digits.count == 4, let hours = Int(digits.prefix(2)), let minutes = Int(digits.suffix(2)) else {
            return nil
        }
        return sign * (hours * 3600 + minutes * 60)
    }
}
