import Foundation

public enum ChildStep: Equatable, Sendable {
    case phone, otp, checkCode, waiting, home
}

public enum ChildRules {
    public static let openStates: Set<String> = ["waiting_push", "calling", "awaiting_answer"]
    private static let inviteAlphabet = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
    private static let caseId = try! NSRegularExpression(
        pattern: "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )

    /// An active membership already passed parent confirm, which required a
    /// verified number, so this install skips the phone step.
    public static func step(status: String, phoneVerified: Bool, checkCodeSet: Bool) -> ChildStep {
        let phoneDone = phoneVerified || status == "active"
        if !phoneDone { return .phone }
        if !checkCodeSet { return .checkCode }
        if status != "active" { return .waiting }
        return .home
    }

    public static func isOpen(_ state: String?) -> Bool { state.map { openStates.contains($0) } ?? false }
    public static func canAnswer(_ state: String?) -> Bool { isOpen(state) }
    public static func canRevealCode(_ state: String?) -> Bool { state == "calling" }

    public static func isCaseId(_ value: String) -> Bool {
        let range = NSRange(value.startIndex..., in: value)
        return caseId.firstMatch(in: value, range: range) != nil
    }

    public static func normalizeInvite(_ raw: String) -> String {
        raw.uppercased().replacingOccurrences(of: "[\\s-]", with: "", options: .regularExpression)
    }

    public static func inviteLooksValid(_ raw: String) -> Bool {
        let secret = normalizeInvite(raw)
        return secret.count == 12 && secret.allSatisfy { inviteAlphabet.contains($0) }
    }
}

public enum BiometricPurpose: Equatable, Sendable {
    case answerYes, answerNo, revealCode, resetCode
}

public enum ChildEffect: Equatable, Sendable {
    case none
    case postAnswer(String)
    case fetchCallCode
    case setCheckCode(code: String, biometricOk: Bool)
}

public struct ChildPrompt: Equatable, Sendable {
    public var prompt: Bool
    public var caseState: String?
    public var revealedCode: String?
    public var callFallback: Bool
    public var resetUnlocked: Bool
    public var pending: BiometricPurpose?

    public init(prompt: Bool = false, caseState: String? = nil, revealedCode: String? = nil, callFallback: Bool = false, resetUnlocked: Bool = false, pending: BiometricPurpose? = nil) {
        self.prompt = prompt
        self.caseState = caseState
        self.revealedCode = revealedCode
        self.callFallback = callFallback
        self.resetUnlocked = resetUnlocked
        self.pending = pending
    }
}

public enum ChildDecisions {
    /// Leaves the question without posting. The case stays open.
    public static func notNow(_ state: ChildPrompt) -> (ChildPrompt, ChildEffect) {
        var next = state
        next.prompt = false
        next.pending = nil
        next.revealedCode = nil
        next.callFallback = false
        return (next, .none)
    }

    public static func ask(_ purpose: BiometricPurpose, _ state: ChildPrompt) -> ChildPrompt? {
        let allowed: Bool = switch purpose {
        case .answerYes, .answerNo: ChildRules.canAnswer(state.caseState)
        case .revealCode: ChildRules.canRevealCode(state.caseState)
        case .resetCode: true
        }
        guard allowed else { return nil }
        var next = state
        next.pending = purpose
        return next
    }

    /// A failed biometric posts nothing and does not reveal a code.
    public static func biometric(_ ok: Bool, _ state: ChildPrompt) -> (ChildPrompt, ChildEffect) {
        guard let purpose = state.pending else { return (state, .none) }
        var next = state
        next.pending = nil
        guard ok else { return (next, .none) }
        switch purpose {
        case .answerYes:
            guard ChildRules.canAnswer(state.caseState) else { return (next, .none) }
            next.revealedCode = nil
            return (next, .postAnswer("yes"))
        case .answerNo:
            guard ChildRules.canAnswer(state.caseState) else { return (next, .none) }
            next.revealedCode = nil
            return (next, .postAnswer("no"))
        case .revealCode:
            guard ChildRules.canRevealCode(state.caseState) else { return (next, .none) }
            return (next, .fetchCallCode)
        case .resetCode:
            next.resetUnlocked = true
            return (next, .none)
        }
    }

    /// Nil unless Face ID already succeeded and the two new entries match.
    /// The returned JSON never contains a previous code.
    public static func resetJSON(first: String, second: String, unlocked: Bool) -> String? {
        guard unlocked, CodeShape.checkCodesMatch(first, second) else { return nil }
        return #"{"biometric_ok":true,"code":"\#(first)"}"#
    }

    public static func applyCallCode(_ code: String?, fallback: String?, to state: ChildPrompt) -> ChildPrompt {
        var next = state
        if let code, CodeShape.isOTP(code) {
            next.revealedCode = code
            next.callFallback = false
        } else {
            next.revealedCode = nil
            next.callFallback = fallback == "static" || code == nil
        }
        return next
    }

    /// The code leaves memory when the case is no longer `calling`.
    public static func retainCode(_ state: ChildPrompt, newState: String) -> ChildPrompt {
        var next = state
        next.caseState = newState
        if newState != "calling" {
            next.revealedCode = nil
            next.callFallback = false
        }
        if !ChildRules.isOpen(newState) { next.prompt = false }
        return next
    }
}

public enum PushAlert {
    public static let kind = "money_request"
    public static let secretKeys: Set<String> = ["code", "otp", "check_code", "one_time_code", "digits", "nonce"]

    public static func title(_ locale: AppLocale) -> String { CopyCatalog.text(.appName, locale) }
    public static func body(_ locale: AppLocale) -> String { CopyCatalog.text(.childNotificationBody, locale) }

    /// The only fields copied onto a tap. A code in the payload is dropped.
    public static func tapInfo(_ data: [String: String]) -> [String: String]? {
        guard data["kind"] == kind, let id = data["case_id"], ChildRules.isCaseId(id) else { return nil }
        return ["kind": kind, "case_id": id]
    }
}

public struct InviteAccepted: Codable, Equatable, Sendable {
    public var memberId: String
    public var familyId: String
    public var displayName: String
    public var status: String
}

public struct OtpStarted: Codable, Equatable, Sendable {
    public var status: String
    public var channel: String
    public var phoneLast4: String
    public var expiresAt: String
}

public struct OtpChecked: Codable, Equatable, Sendable {
    public var status: String
    public var phoneLast4: String
}

public struct StatusBody: Codable, Equatable, Sendable {
    public var status: String
}

public struct CallCode: Codable, Equatable, Sendable {
    public var code: String?
    public var fallback: String?
    public init(code: String? = nil, fallback: String? = nil) {
        self.code = code
        self.fallback = fallback
    }
}

public struct ChildCase: Codable, Equatable, Sendable {
    public var id: String
    public var childMemberId: String
    public var kind: String
    public var state: String
    public var result: String?
    public var color: String
    public var answeredVia: String?
    public var codeChannel: String?
    public var gather: String?
    public var deadlineAt: String?
    public var createdAt: String
    public var updatedAt: String
    public var decidedAt: String?
    /// Parent membership that opened the case. Never a name taken from the message.
    public var askerDisplayName: String?
    /// Claimed amount from the message, or nil. Not a verified transfer.
    public var requestAmount: String?

    public init(id: String, childMemberId: String = "child", kind: String = "money_request", state: String, result: String? = nil, color: String, answeredVia: String? = nil, codeChannel: String? = nil, gather: String? = nil, deadlineAt: String? = nil, createdAt: String = "2026-11-07T00:00:00+00:00", updatedAt: String = "2026-11-07T00:00:00+00:00", decidedAt: String? = nil, askerDisplayName: String? = nil, requestAmount: String? = nil) {
        self.id = id
        self.childMemberId = childMemberId
        self.kind = kind
        self.state = state
        self.result = result
        self.color = color
        self.answeredVia = answeredVia
        self.codeChannel = codeChannel
        self.gather = gather
        self.deadlineAt = deadlineAt
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.decidedAt = decidedAt
        self.askerDisplayName = askerDisplayName
        self.requestAmount = requestAmount
    }
}
