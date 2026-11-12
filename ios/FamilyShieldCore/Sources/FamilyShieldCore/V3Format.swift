import Foundation

/// Countdown and name helpers for the v3 screens. The bar is a 90 second clock, not a score.
public enum V3Format {
    public static let pushWindowSeconds = 90
    public static let segmentSeconds = 3

    public static func remainingSeconds(deadline: Date?, now: Date) -> Int? {
        guard let deadline else { return nil }
        return max(0, Int(deadline.timeIntervalSince(now).rounded(.down)))
    }

    public static func clock(_ seconds: Int) -> String {
        let safe = max(0, seconds)
        return String(format: "%02d:%02d", safe / 60, safe % 60)
    }

    public static func segmentCount(windowSeconds: Int = pushWindowSeconds, segmentSeconds: Int = segmentSeconds) -> Int {
        windowSeconds / segmentSeconds
    }

    /// Index of the lime segment. -1 when the push window is over.
    public static func currentSegment(remainingSeconds: Int, windowSeconds: Int = pushWindowSeconds, segmentSeconds: Int = segmentSeconds) -> Int {
        if remainingSeconds <= 0 { return -1 }
        let elapsed = min(max(0, windowSeconds - remainingSeconds), windowSeconds)
        let last = segmentCount(windowSeconds: windowSeconds, segmentSeconds: segmentSeconds) - 1
        return min(max(0, elapsed / segmentSeconds), last)
    }

    /// Korean subject particle. Names outside Hangul use 가, matching the mockup's 지우가.
    public static func subjectParticle(_ name: String) -> String {
        guard let last = name.unicodeScalars.last else { return "가" }
        let code = last.value
        guard (0xAC00...0xD7A3).contains(code) else { return "가" }
        let hasBatchim = (code - 0xAC00) % 28 != 0
        return hasBatchim ? "이" : "가"
    }

    public static func subject(_ name: String, korean: Bool) -> String {
        korean && !name.isEmpty ? name + subjectParticle(name) : name
    }

    public static func initial(_ name: String) -> String {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.first.map(String.init) ?? ""
    }
}
