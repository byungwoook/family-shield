import Foundation

/// One identification entry for the number Family Shield calls from.
/// The label is always "Family Shield". A different number, including the
/// child's, is absent. This is not a list of scam numbers, and it does not
/// decide that a caller is genuine.
public enum OutboundIdentification {
    public static let label = "Family Shield"
    /// Reserved fictional NANP number (555-0100). Not a Twilio account.
    public static let placeholderE164 = "+15555550100"
    public static let extensionBundleId = "com.familyshield.app.calldirectory"

    public struct Entry: Equatable, Sendable {
        public let phoneNumber: Int64
        public let label: String
        public init(phoneNumber: Int64, label: String) {
            self.phoneNumber = phoneNumber
            self.label = label
        }
    }

    public struct RingDecision: Equatable, Sendable {
        public let disallowCall: Bool
        public let rejectCall: Bool
        public let silenceCall: Bool
        public let announceFamilyShield: Bool

        public init(disallowCall: Bool, rejectCall: Bool, silenceCall: Bool, announceFamilyShield: Bool) {
            self.disallowCall = disallowCall
            self.rejectCall = rejectCall
            self.silenceCall = silenceCall
            self.announceFamilyShield = announceFamilyShield
        }
    }

    /// Zero or one entry. Call Directory wants numbers in ascending order;
    /// a single entry already satisfies that. A list, a blank, or anything
    /// that is not one E.164 value yields nothing.
    public static func entries(configured: String) -> [Entry] {
        guard let number = singleE164(configured) else { return [] }
        return [Entry(phoneNumber: number, label: label)]
    }

    /// Every call is allowed to ring. `announceFamilyShield` is true only
    /// when `incoming` is the same number as `configured`.
    public static func plan(incoming: String?, configured: String) -> RingDecision {
        RingDecision(
            disallowCall: false,
            rejectCall: false,
            silenceCall: false,
            announceFamilyShield: sameNumber(incoming, configured)
        )
    }

    public static func singleE164(_ configured: String) -> Int64? {
        let trimmed = configured.trimmingCharacters(in: .whitespacesAndNewlines)
        guard isSingleE164(trimmed) else { return nil }
        return Int64(trimmed.dropFirst())
    }

    /// `+` then 7 to 15 digits, first digit not zero. A space, a comma, or a second number fails.
    private static func isSingleE164(_ value: String) -> Bool {
        guard value.count >= 8, value.count <= 16, value.first == "+" else { return false }
        let digits = value.dropFirst()
        guard let first = digits.first, first >= "1", first <= "9" else { return false }
        return digits.allSatisfy { $0.isASCII && $0.isNumber }
    }

    private static func sameNumber(_ incoming: String?, _ configured: String) -> Bool {
        guard let ours = singleE164(configured), let incoming else { return false }
        return digits(of: incoming) == ours
    }

    static func digits(of raw: String) -> Int64? {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.filter({ $0 == "+" }).count > 1 { return nil }
        let only = trimmed.filter { $0.isASCII && $0.isNumber }
        guard (7...15).contains(only.count), !only.hasPrefix("0") else { return nil }
        return Int64(only)
    }
}
