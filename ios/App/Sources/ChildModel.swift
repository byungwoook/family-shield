import FamilyShieldCore
import Foundation
import Observation

/// Two booleans per membership. Never a check code or a one-time code.
struct ChildFlags {
    private let defaults: UserDefaults
    init(defaults: UserDefaults = .standard) { self.defaults = defaults }
    func phoneVerified(_ id: String) -> Bool { defaults.bool(forKey: "fs.phone.\(id)") }
    func markPhone(_ id: String) { defaults.set(true, forKey: "fs.phone.\(id)") }
    func checkCodeSet(_ id: String) -> Bool { defaults.bool(forKey: "fs.code.\(id)") }
    func markCode(_ id: String) { defaults.set(true, forKey: "fs.code.\(id)") }
}

@MainActor
@Observable
final class ChildModel {
    let memberId: String
    var familyName: String
    var status: String
    var step: ChildStep
    var phone = ""
    var phoneE164 = ""
    var phoneLast4: String?
    var otp = ""
    var code = ""
    var codeAgain = ""
    var busy = false
    var error: String?
    var notice: String?
    var prompt = ChildPrompt()
    var caseId: String?
    var childCase: ChildCase?
    var resetOpen = false
    private let api: APIClient
    private let flags: ChildFlags
    private var polling = false

    init(child: ChildDestination, api: APIClient, flags: ChildFlags = ChildFlags()) {
        memberId = child.memberId
        familyName = child.familyName
        status = child.status
        self.api = api
        self.flags = flags
        step = ChildRules.step(status: child.status, phoneVerified: flags.phoneVerified(child.memberId), checkCodeSet: flags.checkCodeSet(child.memberId))
    }

    func submitPhone(channel: String) async {
        guard !busy else { return }
        let target: String
        if step == .otp, !phoneE164.isEmpty {
            target = phoneE164
        } else {
            switch PhoneInput.parse(phone) {
            case .valid(let e164): target = e164
            case .invalid:
                error = CopyCatalog.text(.errorInvalidPhone, AppLocale.resolve())
                return
            case .unsupportedCountry:
                error = CopyCatalog.text(.errorUnsupportedCountry, AppLocale.resolve())
                return
            }
        }
        busy = true
        error = nil
        phoneE164 = target
        do {
            let started = try await api.startOtp(phoneE164: target, channel: channel, biometricOk: false)
            busy = false
            step = .otp
            phoneLast4 = started.phoneLast4
            otp = ""
        } catch let failure as APIError {
            busy = false
            if case .http(_, let code) = failure, code == "phone_already_set" {
                flags.markPhone(memberId)
                step = landed()
                notice = CopyCatalog.text(.childPhoneAlready, AppLocale.resolve())
            } else {
                error = otpMessage(failure)
            }
        } catch {
            busy = false
            self.error = CopyCatalog.text(.errorGeneric, AppLocale.resolve())
        }
    }

    func submitOtp() async {
        guard !busy else { return }
        guard CodeShape.isOTP(otp), !phoneE164.isEmpty else {
            error = CopyCatalog.text(.errorOtpWrong, AppLocale.resolve())
            return
        }
        busy = true
        error = nil
        do {
            _ = try await api.checkOtp(phoneE164: phoneE164, code: otp)
            flags.markPhone(memberId)
            busy = false
            otp = ""
            step = landed()
        } catch let failure as APIError {
            busy = false
            error = otpMessage(failure)
        } catch {
            busy = false
            self.error = CopyCatalog.text(.errorGeneric, AppLocale.resolve())
        }
    }

    func submitCheckCode() async {
        guard !busy, let digits = validated() else { return }
        busy = true
        error = nil
        do {
            _ = try await api.setCheckCode(digits, biometricOk: false)
            flags.markCode(memberId)
            busy = false
            code = ""
            codeAgain = ""
            step = landed()
        } catch let failure as APIError {
            busy = false
            if case .http(_, let server) = failure, server == "biometric_required" {
                flags.markCode(memberId)
                code = ""
                codeAgain = ""
                step = landed()
                notice = CopyCatalog.text(.childCodeExists, AppLocale.resolve())
            } else {
                error = CopyCatalog.text(ErrorCopy.key(for: failure), AppLocale.resolve())
            }
        } catch {
            busy = false
            self.error = CopyCatalog.text(.errorGeneric, AppLocale.resolve())
        }
    }

    func openAlert(_ id: String) async {
        guard ChildRules.isCaseId(id) else { return }
        caseId = id
        prompt = ChildPrompt(prompt: true, caseState: prompt.caseState)
        await reload(id)
    }

    func notNow() {
        let (next, effect) = ChildDecisions.notNow(prompt)
        prompt = next
        assertEffectPostsNothing(effect)
    }

    func requestYes() { ask(.answerYes) }
    func requestNo() { ask(.answerNo) }
    func requestReveal() { ask(.revealCode) }

    func requestReset() {
        code = ""
        codeAgain = ""
        prompt.revealedCode = nil
        resetOpen = true
        if let next = ChildDecisions.ask(.resetCode, prompt) { prompt = next }
    }

    func biometricFinished(_ ok: Bool) async {
        let (next, effect) = ChildDecisions.biometric(ok, prompt)
        prompt = next
        switch effect {
        case .none:
            break
        case .postAnswer(let answer):
            await post(answer)
        case .fetchCallCode:
            await fetchCode()
        case .setCheckCode:
            break
        }
    }

    func hideCode() {
        prompt.revealedCode = nil
        prompt.callFallback = false
    }

    func submitReset() async {
        guard !busy else { return }
        guard let json = ChildDecisions.resetJSON(first: code, second: codeAgain, unlocked: prompt.resetUnlocked) else {
            if !prompt.resetUnlocked { return }
            if !CodeShape.isCheckCode(code) {
                error = CopyCatalog.text(.errorInvalidCode, AppLocale.resolve())
            } else {
                error = CopyCatalog.text(.childCodeMismatch, AppLocale.resolve())
            }
            return
        }
        guard let digits = codeAndFlag(json) else { return }
        busy = true
        error = nil
        do {
            _ = try await api.setCheckCode(digits, biometricOk: true)
            flags.markCode(memberId)
            busy = false
            code = ""
            codeAgain = ""
            resetOpen = false
            prompt.resetUnlocked = false
            notice = CopyCatalog.text(.childResetDone, AppLocale.resolve())
        } catch let failure as APIError {
            busy = false
            error = CopyCatalog.text(ErrorCopy.key(for: failure), AppLocale.resolve())
        } catch {
            busy = false
            self.error = CopyCatalog.text(.errorGeneric, AppLocale.resolve())
        }
    }

    func refreshMembership() async { /* the parent view reloads /v1/me */ }

    func pollIfNeeded() async {
        guard !polling else { return }
        polling = true
        defer { polling = false }
        while !Task.isCancelled {
            guard let id = caseId else { return }
            if let state = prompt.caseState, !ChildRules.isOpen(state), childCase != nil { return }
            await reload(id)
            if let state = childCase?.state, !ChildRules.isOpen(state) { return }
            try? await Task.sleep(nanoseconds: 3_000_000_000)
        }
    }

    private func ask(_ purpose: BiometricPurpose) {
        guard let next = ChildDecisions.ask(purpose, prompt) else { return }
        prompt = next
    }

    private func post(_ answer: String) async {
        guard let id = caseId else { return }
        busy = true
        do {
            let fresh = try await api.answerCase(caseId: id, answer: answer)
            childCase = fresh
            prompt = ChildDecisions.retainCode(prompt, newState: fresh.state)
            prompt.prompt = ChildRules.isOpen(fresh.state)
            prompt.revealedCode = nil
            busy = false
        } catch let failure as APIError {
            busy = false
            if case .http(let status, _) = failure, status == 401 { return }
            error = CopyCatalog.text(ErrorCopy.key(for: failure), AppLocale.resolve())
        } catch {
            busy = false
            self.error = CopyCatalog.text(.errorGeneric, AppLocale.resolve())
        }
    }

    private func fetchCode() async {
        guard let id = caseId, ChildRules.canRevealCode(prompt.caseState) else { return }
        do {
            let body = try await api.callCode(caseId: id)
            prompt = ChildDecisions.applyCallCode(body.code, fallback: body.fallback, to: prompt)
        } catch let failure as APIError {
            if case .http(let status, _) = failure, status == 401 { return }
            prompt.revealedCode = nil
            error = CopyCatalog.text(ErrorCopy.key(for: failure), AppLocale.resolve())
        } catch {
            self.error = CopyCatalog.text(.errorGeneric, AppLocale.resolve())
        }
    }

    private func reload(_ id: String) async {
        do {
            let fresh = try await api.childCase(caseId: id)
            childCase = fresh
            prompt = ChildDecisions.retainCode(prompt, newState: fresh.state)
        } catch let failure as APIError {
            if case .http(let status, _) = failure, status == 401 { return }
            error = CopyCatalog.text(ErrorCopy.key(for: failure), AppLocale.resolve())
        } catch {
            self.error = CopyCatalog.text(.errorGeneric, AppLocale.resolve())
        }
    }

    private func validated() -> String? {
        if !CodeShape.isCheckCode(code) {
            error = CopyCatalog.text(.errorInvalidCode, AppLocale.resolve())
            return nil
        }
        if !CodeShape.checkCodesMatch(code, codeAgain) {
            error = CopyCatalog.text(.childCodeMismatch, AppLocale.resolve())
            return nil
        }
        return code
    }

    private func landed() -> ChildStep {
        ChildRules.step(status: status, phoneVerified: flags.phoneVerified(memberId), checkCodeSet: flags.checkCodeSet(memberId))
    }

    private func otpMessage(_ failure: APIError) -> String {
        if case .http(_, let code) = failure, code == "rate_limited" {
            return CopyCatalog.text(.errorOtpRateLimited, AppLocale.resolve())
        }
        return CopyCatalog.text(ErrorCopy.key(for: failure), AppLocale.resolve())
    }

    private func codeAndFlag(_ json: String) -> String? {
        guard let data = json.data(using: .utf8),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let code = object["code"] as? String,
              object["biometric_ok"] as? Bool == true
        else { return nil }
        return code
    }

    private func assertEffectPostsNothing(_ effect: ChildEffect) {
        if case .none = effect { return }
        error = CopyCatalog.text(.errorGeneric, AppLocale.resolve())
    }
}
