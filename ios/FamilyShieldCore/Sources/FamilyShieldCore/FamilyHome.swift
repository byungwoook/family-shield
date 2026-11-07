import Foundation

public enum ChildStage: Equatable, Sendable {
    case ready
    case awaitingConfirm
    case invited
    case inviteExpired
    case joinedNoNumber
    case callOnlyLinkSent
    case notReady
}

public enum MemberRules {
    public static func isChild(_ member: Member) -> Bool { member.role == "child" }

    /// Enable Verify only for a child who is active and confirmed. The server
    /// is still the final judge (`400 member_not_callable`).
    public static func canVerify(_ member: Member) -> Bool {
        isChild(member) && member.status == "active" && member.confirmedAt != nil
    }

    public static func stage(_ member: Member, now: Date = Date()) -> ChildStage {
        if canVerify(member) { return .ready }
        if member.awaitingConfirm { return .awaitingConfirm }
        if member.callOnly && member.status == "invited" { return .callOnlyLinkSent }
        if member.status == "invited" && member.linked && !member.phoneVerified { return .joinedNoNumber }
        if member.status == "invited" && !member.linked {
            if let expires = Times.parse(member.inviteExpiresAt), expires <= now { return .inviteExpired }
            return .invited
        }
        return .notReady
    }

    public static func canReissueInvite(_ member: Member) -> Bool {
        isChild(member) && member.status == "invited" && !member.linked && !member.callOnly
    }

    public static func canAddCallOnly(_ member: Member) -> Bool {
        isChild(member) && member.status == "invited" && !member.linked && member.phoneLast4 == nil
    }

    public static func hasPendingNumber(_ member: Member) -> Bool {
        isChild(member) && member.pendingPhoneLast4 != nil
    }
}

public struct ChildCardState: Equatable, Sendable, Identifiable {
    public var id: String
    public var name: String
    public var statusLine: String
    public var canVerify: Bool
    public var joinRequest: String?
    public var joinHint: String?
    public var phoneChange: String?
    public var phoneChangeHint: String?
    public var canReissue: Bool
    public var canCallOnly: Bool
}

public struct RecentCaseState: Equatable, Sendable, Identifiable {
    public var id: String
    public var title: String
    public var subtitle: String
}

public struct FamilyHomeState: Equatable, Sendable {
    public var familyName: String
    public var children: [ChildCardState]
    public var recent: [RecentCaseState]
    public var isEmpty: Bool { children.isEmpty }
}

public enum FamilyHomeBuilder {
    public static func make(
        familyName: String,
        members: [Member],
        recent: [CaseSummary],
        locale: AppLocale,
        formattingLocale: Locale,
        now: Date = Date(),
        timeZone: TimeZone = .current
    ) -> FamilyHomeState {
        let shownName = familyName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? CopyCatalog.text(.familyTitleFallback, locale)
            : familyName
        let children = members.filter(MemberRules.isChild).map { member in
            card(member, locale: locale, formattingLocale: formattingLocale, now: now, timeZone: timeZone)
        }
        let rows = recent.map { summary in
            RecentCaseState(
                id: summary.id,
                title: summary.childDisplayName.isEmpty ? CopyCatalog.text(.cdChild, locale) : summary.childDisplayName,
                subtitle: rowLabel(summary.color, decidedAt: summary.decidedAt, locale: locale)
            )
        }
        return FamilyHomeState(familyName: shownName, children: children, recent: rows)
    }

    private static func card(_ member: Member, locale: AppLocale, formattingLocale: Locale, now: Date, timeZone: TimeZone) -> ChildCardState {
        let stage = MemberRules.stage(member, now: now)
        let name = member.displayName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? CopyCatalog.text(.cdChild, locale)
            : member.displayName
        let last4 = member.phoneLast4 ?? ""
        let expires = Times.shortDateTime(member.inviteExpiresAt, locale: formattingLocale, timeZone: timeZone)
        let line: String = switch stage {
        case .ready:
            last4.isEmpty
                ? CopyCatalog.text(.childReadyNoNumber, locale)
                : CopyCatalog.text(.childReady, locale, name, last4)
        case .awaitingConfirm:
            CopyCatalog.text(.childAwaitingConfirm, locale, name)
        case .invited:
            CopyCatalog.text(.childInvited, locale, name, expires)
        case .inviteExpired:
            CopyCatalog.text(.childInviteExpired, locale, name)
        case .joinedNoNumber:
            CopyCatalog.text(.childJoinedNoNumber, locale, name)
        case .callOnlyLinkSent:
            CopyCatalog.text(.childCallOnlyLinkSent, locale, name, last4)
        case .notReady:
            CopyCatalog.text(.childNotReady, locale, name)
        }
        return ChildCardState(
            id: member.id,
            name: name,
            statusLine: line,
            canVerify: MemberRules.canVerify(member),
            joinRequest: member.awaitingConfirm ? CopyCatalog.text(.joinRequest, locale, name, last4) : nil,
            joinHint: member.awaitingConfirm ? CopyCatalog.text(.joinRequestHint, locale) : nil,
            phoneChange: MemberRules.hasPendingNumber(member)
                ? CopyCatalog.text(.phoneChangeRequest, locale, name, member.pendingPhoneLast4 ?? "")
                : nil,
            phoneChangeHint: MemberRules.hasPendingNumber(member)
                ? CopyCatalog.text(.phoneChangeHint, locale, name)
                : nil,
            canReissue: MemberRules.canReissueInvite(member),
            canCallOnly: MemberRules.canAddCallOnly(member)
        )
    }

    private static func rowLabel(_ color: String, decidedAt: String?, locale: AppLocale) -> String {
        switch CaseColor.of(color, decidedAt: decidedAt) {
        case .open: return CopyCatalog.text(.caseRowOpen, locale)
        case .green: return CopyCatalog.text(.caseRowGreen, locale)
        case .red: return CopyCatalog.text(.caseRowRed, locale)
        case .yellow: return CopyCatalog.text(.caseRowYellow, locale)
        }
    }
}

public enum ParentFixture: String, CaseIterable, Sendable {
    case emptyFamily
    case verifyDisabled
    case yellow
    case red
    case shareDraft
    case notNow
    case resetLocked
}

public enum ParentFixtures {
    public static let childId = "11111111-1111-1111-1111-111111111111"
    public static let caseId = "22222222-2222-2222-2222-222222222222"

    public static func home(_ fixture: ParentFixture, locale: AppLocale, now: Date) -> FamilyHomeState? {
        switch fixture {
        case .emptyFamily:
            return FamilyHomeBuilder.make(familyName: "Lee", members: [], recent: [], locale: locale, formattingLocale: Locale(identifier: locale == .ko ? "ko_KR" : "en_US"), now: now)
        case .verifyDisabled:
            let pending = Member(
                id: childId,
                role: "child",
                displayName: "Minji",
                status: "invited",
                linked: true,
                phoneLast4: "0123",
                phoneVerified: true,
                awaitingConfirm: true
            )
            return FamilyHomeBuilder.make(familyName: "Lee", members: [pending], recent: [], locale: locale, formattingLocale: Locale(identifier: "en_US"), now: now)
        case .yellow, .red, .shareDraft, .notNow, .resetLocked:
            return nil
        }
    }

    public static func caseItem(_ fixture: ParentFixture) -> ParentCase? {
        switch fixture {
        case .yellow:
            return ParentCase(
                id: caseId,
                childDisplayName: "Minji",
                state: "not_confirmed",
                result: "wrong",
                color: "yellow",
                parentText: "Please send gift cards tonight",
                timeline: ["start", "static_code_mismatch"],
                decidedAt: "2026-11-07T03:42:00+00:00"
            )
        case .red:
            return ParentCase(
                id: caseId,
                childDisplayName: "Minji",
                state: "scam",
                result: "not_sent",
                color: "red",
                claims: Claims(story: "tuition is due tonight"),
                patternId: "tuition_or_school",
                timeline: ["start", "push_answered_no"],
                decidedAt: "2026-11-07T03:42:00+00:00"
            )
        case .emptyFamily, .verifyDisabled, .shareDraft, .notNow, .resetLocked:
            return nil
        }
    }
}
