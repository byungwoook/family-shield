import FamilyShieldCore
import SwiftUI

struct ChildHost: View {
    var app: AppModel
    var child: ChildDestination
    @State private var model: ChildModel?

    var body: some View {
        Group {
            if let model {
                ChildFlow(model: model, onSignOut: {
                    app.discardShare()
                    app.signOut()
                }, onRefresh: {
                    Task { await app.reload() }
                })
            } else {
                ProgressView(CopyCatalog.text(.loading, AppLocale.resolve()))
            }
        }
        .task(id: child.memberId) {
            if model == nil { model = ChildModel(child: child, api: app.api) }
            if let id = app.childCaseId { await model?.openAlert(id) }
        }
        .onChange(of: app.childCaseId) { _, id in
            guard let id else { return }
            Task { await model?.openAlert(id) }
        }
    }
}

struct ChildFlow: View {
    @Bindable var model: ChildModel
    var onSignOut: () -> Void
    var onRefresh: () -> Void
    private var locale: AppLocale { AppLocale.resolve() }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Text(model.familyName.isEmpty ? CopyCatalog.text(.familyTitleFallback, locale) : model.familyName)
                        .font(.title2)
                    Spacer()
                    Button(CopyCatalog.text(.actionSignOut, locale), action: onSignOut)
                }
                if let notice = model.notice { Banner(text: notice, tone: Theme.accent) }
                if let error = model.error { Banner(text: error) }
                if model.prompt.prompt {
                    QuestionView(model: model)
                } else if model.resetOpen {
                    ResetView(model: model)
                } else {
                    switch model.step {
                    case .phone: PhoneView(model: model)
                    case .otp: OtpView(model: model)
                    case .checkCode: CheckCodeView(model: model, replacing: false)
                    case .waiting: WaitingView(model: model, onRefresh: onRefresh)
                    case .home: HomeView(model: model)
                    }
                }
            }
            .padding(16)
        }
        .task { await model.pollIfNeeded() }
    }
}

private struct PhoneView: View {
    @Bindable var model: ChildModel
    private var locale: AppLocale { AppLocale.resolve() }
    var body: some View {
        Text(CopyCatalog.text(.childPhoneTitle, locale)).font(.title3)
        Text(CopyCatalog.text(.childPhoneBody, locale))
        TextField(CopyCatalog.text(.childPhoneLabel, locale), text: $model.phone)
            .textFieldStyle(.roundedBorder)
            .keyboardType(.phonePad)
            .accessibilityIdentifier("child_phone")
        PrimaryButton(title: CopyCatalog.text(.childPhoneSubmit, locale), identifier: "send_otp", enabled: !model.busy) {
            Task { await model.submitPhone(channel: "sms") }
        }
    }
}

private struct OtpView: View {
    @Bindable var model: ChildModel
    private var locale: AppLocale { AppLocale.resolve() }
    var body: some View {
        Text(CopyCatalog.text(.childOtpTitle, locale)).font(.title3)
        if let last4 = model.phoneLast4 {
            Text(CopyCatalog.text(.childOtpBody, locale, last4))
        } else {
            Text(CopyCatalog.text(.childOtpBodyPlain, locale))
        }
        TextField(CopyCatalog.text(.childOtpLabel, locale), text: $model.otp)
            .textFieldStyle(.roundedBorder)
            .keyboardType(.numberPad)
            .onChange(of: model.otp) { _, value in model.otp = CodeShape.digits(value, max: 6) }
            .accessibilityIdentifier("child_otp")
        PrimaryButton(title: CopyCatalog.text(.childOtpSubmit, locale), identifier: "check_otp", enabled: !model.busy) {
            Task { await model.submitOtp() }
        }
        Button(CopyCatalog.text(.childOtpVoice, locale)) { Task { await model.submitPhone(channel: "voice") } }
            .disabled(model.busy)
        Button(CopyCatalog.text(.childOtpResend, locale)) { Task { await model.submitPhone(channel: "sms") } }
            .disabled(model.busy)
    }
}

private struct CheckCodeView: View {
    @Bindable var model: ChildModel
    var replacing: Bool
    private var locale: AppLocale { AppLocale.resolve() }
    var body: some View {
        Text(CopyCatalog.text(replacing ? .childResetTitle : .childCodeTitle, locale)).font(.title3)
        Text(CopyCatalog.text(replacing ? .childResetBody : .childCodeBody, locale))
        TextField(CopyCatalog.text(.childCodeLabel, locale), text: $model.code)
            .textFieldStyle(.roundedBorder)
            .keyboardType(.numberPad)
            .onChange(of: model.code) { _, value in model.code = CodeShape.digits(value, max: 4) }
            .accessibilityIdentifier("check_code")
        TextField(CopyCatalog.text(.childCodeAgainLabel, locale), text: $model.codeAgain)
            .textFieldStyle(.roundedBorder)
            .keyboardType(.numberPad)
            .onChange(of: model.codeAgain) { _, value in model.codeAgain = CodeShape.digits(value, max: 4) }
            .accessibilityIdentifier("check_code_again")
        PrimaryButton(title: CopyCatalog.text(replacing ? .childResetSubmit : .childCodeSubmit, locale), identifier: "save_code", enabled: !model.busy) {
            Task { if replacing { await model.submitReset() } else { await model.submitCheckCode() } }
        }
    }
}

private struct WaitingView: View {
    var model: ChildModel
    var onRefresh: () -> Void
    private var locale: AppLocale { AppLocale.resolve() }
    var body: some View {
        Text(CopyCatalog.text(.childWaitingTitle, locale)).font(.title3)
        if let last4 = model.phoneLast4 {
            Text(CopyCatalog.text(.childWaitingBodyNumber, locale, last4))
        } else {
            Text(CopyCatalog.text(.childWaitingBody, locale))
        }
        Button(CopyCatalog.text(.childWaitingRefresh, locale), action: onRefresh)
        OutboundLabelCard()
    }
}

private struct HomeView: View {
    @Bindable var model: ChildModel
    private var locale: AppLocale { AppLocale.resolve() }
    var body: some View {
        if let item = model.childCase, ChildRules.isOpen(item.state) {
            Text(CopyCatalog.text(.childHomeWaiting, locale))
            Button(CopyCatalog.text(.childHomeAnswer, locale)) { model.prompt.prompt = true }
        } else if let item = model.childCase {
            Text(resultLine(item))
        } else {
            Text(CopyCatalog.text(.childHomeIdle, locale))
        }
        Button(CopyCatalog.text(.childHomeReset, locale)) { model.requestReset() }
            .accessibilityIdentifier("reset_code")
        OutboundLabelCard()
    }

    private func resultLine(_ item: ChildCase) -> String {
        if item.result == "sent" { return CopyCatalog.text(.childResultYes, locale) }
        if item.result == "not_sent" { return CopyCatalog.text(.childResultNo, locale) }
        return CopyCatalog.text(.childResultClosed, locale)
    }
}

private struct OutboundLabelCard: View {
    @Environment(\.scenePhase) private var scenePhase
    @State private var enabled = false
    private var locale: AppLocale { AppLocale.resolve() }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(CopyCatalog.text(.outboundLabelTitle, locale)).font(.headline)
            Text(CopyCatalog.text(enabled ? .outboundLabelOn : .outboundLabelOff, locale))
            Text(CopyCatalog.text(.outboundLabelBody, locale)).font(.footnote)
            Button(CopyCatalog.text(.outboundLabelOpenSettings, locale)) {
                CallDirectoryLink.openSettings()
            }
            .accessibilityIdentifier("open_call_directory")
        }
        .accessibilityIdentifier("outbound_label")
        .onAppear { refresh() }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active { refresh() }
        }
    }

    private func refresh() {
        CallDirectoryLink.reload()
        CallDirectoryLink.refresh { enabled = $0 }
    }
}

private struct QuestionView: View {
    @Bindable var model: ChildModel
    private var locale: AppLocale { AppLocale.resolve() }
    var body: some View {
        Text(CopyCatalog.text(.childQuestion, locale)).font(.title3).accessibilityIdentifier("child_question")
        Text(CopyCatalog.text(.childQuestionHint, locale))
        if ChildRules.canAnswer(model.prompt.caseState) {
            PrimaryButton(title: CopyCatalog.text(.childYes, locale), identifier: "answer_yes", enabled: !model.busy) {
                Task { await confirm(.answerYes, CopyCatalog.text(.biometricTitleAnswer, locale)) }
            }
            Button(CopyCatalog.text(.childNo, locale)) {
                Task { await confirm(.answerNo, CopyCatalog.text(.biometricTitleAnswer, locale)) }
            }
            .buttonStyle(.bordered)
            .disabled(model.busy)
            .accessibilityIdentifier("answer_no")
        }
        Button(CopyCatalog.text(.childNotNow, locale)) { model.notNow() }
            .accessibilityIdentifier("not_now")
        if ChildRules.canRevealCode(model.prompt.caseState) {
            Text(CopyCatalog.text(.childRevealHint, locale))
            if let code = model.prompt.revealedCode {
                Text(code).font(.largeTitle.monospaced()).accessibilityIdentifier("one_time_code")
                Text(CopyCatalog.text(.childCodeShown, locale))
                Button(CopyCatalog.text(.childHideCode, locale)) { model.hideCode() }
            } else if model.prompt.callFallback {
                Text(CopyCatalog.text(.childFallbackStatic, locale)).accessibilityIdentifier("call_fallback")
            } else {
                Button(CopyCatalog.text(.childReveal, locale)) {
                    Task { await confirm(.revealCode, CopyCatalog.text(.biometricTitleCode, locale)) }
                }
                .accessibilityIdentifier("reveal_code")
            }
        }
    }

    private func confirm(_ purpose: BiometricPurpose, _ reason: String) async {
        switch purpose {
        case .answerYes: model.requestYes()
        case .answerNo: model.requestNo()
        case .revealCode: model.requestReveal()
        case .resetCode: break
        }
        let ok = await FaceIDGate.confirm(reason)
        await model.biometricFinished(ok)
    }
}

private struct ResetView: View {
    @Bindable var model: ChildModel
    private var locale: AppLocale { AppLocale.resolve() }
    var body: some View {
        Text(CopyCatalog.text(.childResetTitle, locale)).font(.title3)
        Text(CopyCatalog.text(.childResetBody, locale))
        if model.prompt.resetUnlocked {
            CheckCodeView(model: model, replacing: true)
        } else {
            Text(CopyCatalog.text(.biometricSubtitle, locale)).font(.footnote)
            PrimaryButton(title: CopyCatalog.text(.childResetUnlock, locale), identifier: "reset_unlock", enabled: !model.busy) {
                Task {
                    model.requestReset()
                    let ok = await FaceIDGate.confirm(CopyCatalog.text(.biometricTitleReset, locale))
                    await model.biometricFinished(ok)
                }
            }
            .accessibilityIdentifier("reset_locked")
        }
        Button(CopyCatalog.text(.actionCancel, locale)) {
            model.resetOpen = false
            model.prompt.resetUnlocked = false
            model.code = ""
            model.codeAgain = ""
        }
    }
}
