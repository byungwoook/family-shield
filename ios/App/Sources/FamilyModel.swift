import FamilyShieldCore
import Foundation
import Observation

struct DraftAudio: Equatable {
    var fileURL: URL
    var displayName: String
    var contentType: String
    var sizeBytes: Int64
}

struct ShownInvite: Equatable {
    var name: String
    var secret: String
    var expiresAt: String
}

@MainActor
@Observable
final class FamilyModel {
    enum Page { case home, newCase }

    private let familyId: String
    private let api: APIClient
    private var members: [Member] = []
    private var recent: [CaseSummary] = []

    var familyName: String
    var home = FamilyHomeState(familyName: "", children: [], recent: [])
    var loading = true
    var busy = false
    var error: String?
    var notice: String?
    var showAdd = false
    var addName = ""
    var addPhone = ""
    var addByPhone = false
    var invite: ShownInvite?
    var callOnlyMemberId: String?
    var page: Page = .home
    var caseChildId: String?
    var caseText = ""
    var draft: DraftAudio?
    var fromShare = false
    private var appliedShareKey: String?

    init(familyId: String, familyName: String, api: APIClient) {
        self.familyId = familyId
        self.familyName = familyName
        self.api = api
        self.home = FamilyHomeState(familyName: familyName, children: [], recent: [])
    }

    func refresh(clearError: Bool = true) async {
        if clearError { error = nil }
        do {
            let roster = try await api.members(familyId: familyId)
            let cases = try await api.familyCases(familyId: familyId)
            members = roster.members
            recent = cases.cases
            rebuild()
            loading = false
        } catch let failure as APIError {
            loading = false
            if case .http(let status, _) = failure, status == 401 { return }
            error = CopyCatalog.text(ErrorCopy.key(for: failure), AppLocale.resolve())
        } catch {
            loading = false
            self.error = CopyCatalog.text(.errorGeneric, AppLocale.resolve())
        }
    }

    func addChild() async {
        let name = addName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty else {
            error = CopyCatalog.text(.errorNameRequired, AppLocale.resolve())
            return
        }
        let phone: String?
        if addByPhone {
            switch PhoneInput.parse(addPhone) {
            case .valid(let e164): phone = e164
            case .invalid:
                error = CopyCatalog.text(.errorInvalidPhone, AppLocale.resolve())
                return
            case .unsupportedCountry:
                error = CopyCatalog.text(.errorUnsupportedCountry, AppLocale.resolve())
                return
            }
        } else {
            phone = nil
        }
        guard !busy else { return }
        busy = true
        error = nil
        do {
            let created = try await api.addChild(familyId: familyId, displayName: String(name.prefix(Limits.name)))
            if let phone {
                do {
                    let sent = try await api.addCallOnly(familyId: familyId, memberId: created.id, phoneE164: phone)
                    invite = nil
                    showAdd = false
                    addName = ""
                    addPhone = ""
                    notice = CopyCatalog.text(.noticeLinkSent, AppLocale.resolve(), name, sent.phoneLast4 ?? "")
                } catch let failure as APIError {
                    // The secret was returned once. Call-only did not burn it, so show it.
                    invite = ShownInvite(name: created.displayName, secret: created.inviteSecret, expiresAt: created.inviteExpiresAt)
                    showAdd = false
                    error = CopyCatalog.text(ErrorCopy.key(for: failure), AppLocale.resolve())
                    busy = false
                    await refresh(clearError: false)
                    return
                }
            } else {
                invite = ShownInvite(name: created.displayName, secret: created.inviteSecret, expiresAt: created.inviteExpiresAt)
                showAdd = false
                addName = ""
                addPhone = ""
            }
            busy = false
            await refresh()
        } catch let failure as APIError {
            busy = false
            error = CopyCatalog.text(ErrorCopy.key(for: failure), AppLocale.resolve())
        } catch {
            busy = false
            self.error = CopyCatalog.text(.errorGeneric, AppLocale.resolve())
        }
    }

    func submitCallOnly() async {
        guard let memberId = callOnlyMemberId else { return }
        let phone: String
        switch PhoneInput.parse(addPhone) {
        case .valid(let e164): phone = e164
        case .invalid:
            error = CopyCatalog.text(.errorInvalidPhone, AppLocale.resolve())
            return
        case .unsupportedCountry:
            error = CopyCatalog.text(.errorUnsupportedCountry, AppLocale.resolve())
            return
        }
        let name = members.first { $0.id == memberId }?.displayName ?? ""
        await run {
            let sent = try await self.api.addCallOnly(familyId: self.familyId, memberId: memberId, phoneE164: phone)
            self.callOnlyMemberId = nil
            self.addPhone = ""
            self.notice = CopyCatalog.text(.noticeLinkSent, AppLocale.resolve(), name, sent.phoneLast4 ?? "")
        }
    }

    func reissue(memberId: String) async {
        let name = members.first { $0.id == memberId }?.displayName ?? ""
        await run {
            let invite = try await self.api.reissueInvite(familyId: self.familyId, memberId: memberId)
            self.invite = ShownInvite(name: name, secret: invite.inviteSecret, expiresAt: invite.inviteExpiresAt)
        }
    }

    func confirmJoin(memberId: String) async { await decideJoin(memberId, .confirm) }
    func rejectJoin(memberId: String) async { await decideJoin(memberId, .reject) }

    func confirmPhone(memberId: String) async { await decidePhone(memberId, .confirm) }
    func rejectPhone(memberId: String) async { await decidePhone(memberId, .reject) }

    func openNewCase(preselect: String? = nil) {
        removeDraft()
        let ready = members.filter(MemberRules.canVerify)
        page = .newCase
        caseChildId = preselect ?? (ready.count == 1 ? ready[0].id : nil)
        caseText = ""
        error = nil
    }

    func closeNewCase() {
        removeDraft()
        fromShare = false
        page = .home
        caseText = ""
        error = nil
    }

    /// A share becomes a draft. The file stays on this phone until Verify.
    func applyShare(text: String, audio: DraftAudio?, problem: ShareProblem?, key: String) {
        guard key != appliedShareKey else { return }
        appliedShareKey = key
        removeDraft()
        let ready = members.filter(MemberRules.canVerify)
        page = .newCase
        caseChildId = ready.count == 1 ? ready[0].id : caseChildId
        caseText = String(text.prefix(Limits.text))
        draft = audio
        fromShare = true
        error = problem.map(Self.problemText)
    }

    func removeDraft() {
        if let url = draft?.fileURL {
            try? FileManager.default.removeItem(at: url)
        }
        draft = nil
    }

    static func problemText(_ problem: ShareProblem) -> String {
        let key: CopyKey = switch problem {
        case .tooLarge: .shareAudioTooLarge
        case .empty: .shareAudioEmpty
        case .unsupported: .shareAudioUnsupported
        case .unreadable: .shareAudioUnreadable
        }
        return CopyCatalog.text(key, AppLocale.resolve())
    }

    func loadCase(_ id: String) async -> ParentCase? {
        do {
            return try await api.parentCase(caseId: id)
        } catch let failure as APIError {
            if case .http(let status, _) = failure, status == 401 { return nil }
            error = CopyCatalog.text(ErrorCopy.key(for: failure), AppLocale.resolve())
            return nil
        } catch {
            self.error = CopyCatalog.text(.errorGeneric, AppLocale.resolve())
            return nil
        }
    }

    func verify() async -> ParentCase? {
        guard let childId = caseChildId else {
            error = CopyCatalog.text(.newCaseNoChildren, AppLocale.resolve())
            return nil
        }
        guard !busy else { return nil }
        busy = true
        error = nil
        do {
            let text = String(caseText.prefix(Limits.text)).trimmingCharacters(in: .whitespacesAndNewlines)
            let audio = draft.map {
                CaseAudio(fileURL: $0.fileURL, uploadName: $0.displayName, contentType: $0.contentType)
            }
            let opened = try await api.openCase(childMemberId: childId, text: text, audio: audio)
            removeDraft()
            busy = false
            page = .home
            caseText = ""
            return opened
        } catch let failure as APIError {
            busy = false
            error = CopyCatalog.text(ErrorCopy.key(for: failure), AppLocale.resolve())
            return nil
        } catch {
            busy = false
            self.error = CopyCatalog.text(.errorGeneric, AppLocale.resolve())
            return nil
        }
    }

    var readyChildren: [ChildCardState] {
        home.children.filter(\.canVerify)
    }

    private func decideJoin(_ memberId: String, _ decision: ParentDecision) async {
        let name = members.first { $0.id == memberId }?.displayName ?? ""
        await run {
            _ = try await self.api.confirmMember(familyId: self.familyId, memberId: memberId, decision: decision)
            self.notice = CopyCatalog.text(decision == .confirm ? .noticeChildConfirmed : .noticeChildRejected, AppLocale.resolve(), name)
        }
    }

    private func decidePhone(_ memberId: String, _ decision: ParentDecision) async {
        let name = members.first { $0.id == memberId }?.displayName ?? ""
        await run {
            let result = try await self.api.decidePhoneChange(familyId: self.familyId, memberId: memberId, decision: decision)
            if decision == .reject {
                self.notice = CopyCatalog.text(.noticeNumberKept, AppLocale.resolve(), name)
            } else if (result.cancelledCases ?? 0) > 0 {
                self.notice = CopyCatalog.text(.noticeNumberChangedCancelled, AppLocale.resolve(), name, result.phoneLast4 ?? "")
            } else {
                self.notice = CopyCatalog.text(.noticeNumberChanged, AppLocale.resolve(), name, result.phoneLast4 ?? "")
            }
        }
    }

    private func run(_ work: () async throws -> Void) async {
        guard !busy else { return }
        busy = true
        error = nil
        do {
            try await work()
            busy = false
            await refresh()
        } catch let failure as APIError {
            busy = false
            if case .http(let status, _) = failure, status == 401 { return }
            error = CopyCatalog.text(ErrorCopy.key(for: failure), AppLocale.resolve())
        } catch {
            busy = false
            self.error = CopyCatalog.text(.errorGeneric, AppLocale.resolve())
        }
    }

    private func rebuild() {
        home = FamilyHomeBuilder.make(
            familyName: familyName,
            members: members,
            recent: recent,
            locale: AppLocale.resolve(),
            formattingLocale: .current
        )
    }
}
