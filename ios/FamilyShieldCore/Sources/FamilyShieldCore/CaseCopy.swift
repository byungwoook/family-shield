import Foundation

/// The colour the parent sees. The server derives `color` from `state` only.
/// A value this app does not know is never shown as green or red.
public enum CaseColor: Equatable, Sendable {
    case open, green, red, yellow

    public var isDecided: Bool { self != .open }

    public static func of(_ wire: String?, decidedAt: String? = nil) -> CaseColor {
        switch wire {
        case "open": return .open
        case "green": return .green
        case "red": return .red
        case "yellow": return .yellow
        default: return decidedAt == nil ? .open : .yellow
        }
    }
}

public enum ResultCode: String, CaseIterable, Sendable {
    case sent
    case notSent = "not_sent"
    case wrong
    case noAnswer = "no_answer"
    case noNumber = "no_number"
    case callFailed = "call_failed"
    case timeout
    case unreachable
    case codeLocked = "code_locked"
    case numberRecent = "number_recent"
}

public struct ResultCopy: Equatable, Sendable {
    public var color: CaseColor
    public var title: CopyKey
    public var body: CopyKey
}

public enum CaseCopy {
    /// Nil while the case is open. Only the colour decides green or red.
    public static func result(color: CaseColor, result: String?) -> ResultCopy? {
        switch color {
        case .open: return nil
        case .green: return ResultCopy(color: .green, title: .resultTitleGreen, body: .resultSent)
        case .red: return ResultCopy(color: .red, title: .resultTitleRed, body: .resultNotSent)
        case .yellow: return ResultCopy(color: .yellow, title: .resultTitleYellow, body: yellowBody(ResultCode(rawValue: result ?? "")))
        }
    }

    public static func yellowBody(_ code: ResultCode?) -> CopyKey {
        switch code {
        case .wrong: return .resultWrong
        case .noAnswer: return .resultNoAnswer
        case .noNumber: return .resultNoNumber
        case .callFailed: return .resultCallFailed
        case .timeout: return .resultTimeout
        case .unreachable: return .resultUnreachable
        case .codeLocked: return .resultCodeLocked
        case .numberRecent: return .resultNumberRecent
        case .sent, .notSent, nil: return .resultYellowGeneric
        }
    }

    public static func openLine(_ state: String) -> CopyKey {
        switch state {
        case "waiting_push": return .openWaitingPush
        case "calling": return .openCalling
        case "awaiting_answer": return .openAwaitingAnswer
        default: return .openStarting
        }
    }

    public static func timelineStep(_ step: String) -> CopyKey {
        timeline[step] ?? .timelineUnknown
    }

    public static let timeline: [String: CopyKey] = [
        "start": .timelineStart,
        "push_answered_yes": .timelinePushAnsweredYes,
        "push_answered_no": .timelinePushAnsweredNo,
        "push_failed": .timelinePushFailed,
        "push_window_elapsed": .timelinePushWindowElapsed,
        "call_failed": .timelineCallFailed,
        "call_busy": .timelineCallBusy,
        "call_no_answer": .timelineCallNoAnswer,
        "call_ended_before_code": .timelineCallEndedBeforeCode,
        "call_ended_before_answer": .timelineCallEndedBeforeAnswer,
        "code_window_elapsed": .timelineCodeWindowElapsed,
        "use_static_code": .timelineUseStaticCode,
        "code_accepted": .timelineCodeAccepted,
        "static_code_mismatch": .timelineStaticCodeMismatch,
        "code_did_not_match": .timelineCodeDidNotMatch,
        "one_time_code_expired": .timelineOneTimeCodeExpired,
        "code_rejected": .timelineCodeRejected,
        "answer_yes": .timelineAnswerYes,
        "answer_no": .timelineAnswerNo,
        "answer_unclear": .timelineAnswerUnclear,
        "answer_window_elapsed": .timelineAnswerWindowElapsed,
        "phone_number_changed": .timelinePhoneNumberChanged,
    ]

    public static let patternLabels: [String: CopyKey] = [
        "fake_arrest_bail": .patternFakeArrestBail,
        "accident": .patternAccident,
        "gift_card": .patternGiftCard,
        "crypto_or_wire": .patternCryptoOrWire,
        "secrecy": .patternSecrecy,
        "tuition_or_school": .patternTuitionOrSchool,
        "new_number": .patternNewNumber,
    ]

    public static func patternLabel(_ patternId: String?) -> CopyKey? {
        guard let patternId else { return nil }
        return patternLabels[patternId]
    }

    /// Under green, the known-pattern warning. Anywhere else it is information
    /// only. It never decides the colour and never says to pay.
    public static func patternLine(_ color: CaseColor) -> CopyKey {
        color == .green ? .patternLineGreen : .patternLineInfo
    }

    public static func offersFamilyAlert(_ color: CaseColor) -> Bool { color == .red }
}

public struct CasePresentation: Equatable, Sendable {
    public var name: String
    public var color: CaseColor
    public var title: String
    public var body: String
    public var dontSend: String?
    public var openLine: String?
    public var checkedAt: String?
    public var patternLine: String?
    public var familyAlert: String?
    public var claimsHeading: String?
    public var claimLines: [String]
    public var parentTextHeading: String?
    public var parentText: String?
    public var timelineHeading: String?
    public var timeline: [String]
    public var updateFailed: String?
}

public enum CasePresenter {
    public static func present(
        _ item: ParentCase,
        locale: AppLocale,
        formattingLocale: Locale,
        timeZone: TimeZone = .current,
        updateFailed: Bool = false
    ) -> CasePresentation {
        let color = CaseColor.of(item.color, decidedAt: item.decidedAt)
        let name = item.childDisplayName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? CopyCatalog.text(.cdChild, locale)
            : item.childDisplayName
        let when = Times.shortTime(item.decidedAt, locale: formattingLocale, timeZone: timeZone)
        let copy = CaseCopy.result(color: color, result: item.result)
        var claims: [String] = []
        var claimsHeading: String?
        if let raw = item.claims {
            if let value = known(raw.claimedIdentity) { claims.append(CopyCatalog.text(.claimsIdentity, locale, value)) }
            if let value = known(raw.amount) { claims.append(CopyCatalog.text(.claimsAmount, locale, value)) }
            if let value = known(raw.story) { claims.append(CopyCatalog.text(.claimsStory, locale, value)) }
            let flags = raw.redFlags.compactMap(known)
            if !flags.isEmpty {
                claims.append(CopyCatalog.text(.claimsRedFlags, locale, flags.joined(separator: CopyCatalog.text(.listSeparator, locale))))
            }
            if !claims.isEmpty { claimsHeading = CopyCatalog.text(.claimsHeading, locale) }
        }
        let story = known(item.claims?.story)
        let alert: String? = CaseCopy.offersFamilyAlert(color)
            ? (story == nil
                ? CopyCatalog.text(.familyAlertMessage, locale, name)
                : CopyCatalog.text(.familyAlertMessageWithStory, locale, name, story ?? ""))
            : nil
        let pattern: String? = {
            guard let label = CaseCopy.patternLabel(item.patternId) else { return nil }
            return CopyCatalog.text(CaseCopy.patternLine(color), locale, CopyCatalog.text(label, locale), name)
        }()
        let text = item.parentText.trimmingCharacters(in: .whitespacesAndNewlines)
        return CasePresentation(
            name: name,
            color: color,
            title: copy.map { CopyCatalog.text($0.title, locale) } ?? "",
            body: copy.map { CopyCatalog.text($0.body, locale, name, when) } ?? "",
            dontSend: color == .open ? CopyCatalog.text(.caseDontSend, locale) : nil,
            openLine: color == .open ? CopyCatalog.text(CaseCopy.openLine(item.state), locale, name) : nil,
            checkedAt: (copy != nil && !when.isEmpty) ? CopyCatalog.text(.caseCheckedAt, locale, when) : nil,
            patternLine: pattern,
            familyAlert: alert,
            claimsHeading: claimsHeading,
            claimLines: claims,
            parentTextHeading: text.isEmpty ? nil : CopyCatalog.text(.caseYourTextHeading, locale),
            parentText: text.isEmpty ? nil : item.parentText,
            timelineHeading: item.timeline.isEmpty ? nil : CopyCatalog.text(.caseTimelineHeading, locale),
            timeline: item.timeline.map { CopyCatalog.text(CaseCopy.timelineStep($0), locale) },
            updateFailed: (updateFailed && color == .open) ? CopyCatalog.text(.caseUpdateFailed, locale) : nil
        )
    }

    static func known(_ raw: String?) -> String? {
        guard let trimmed = raw?.trimmingCharacters(in: .whitespacesAndNewlines), !trimmed.isEmpty else { return nil }
        if trimmed.compare("unknown", options: .caseInsensitive) == .orderedSame { return nil }
        return trimmed
    }
}
