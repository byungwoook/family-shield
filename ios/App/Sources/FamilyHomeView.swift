import FamilyShieldCore
import SwiftUI

struct FamilyFlow: View {
    @Bindable var model: FamilyModel
    var onOpened: (ParentCase) -> Void
    var onSignOut: () -> Void
    var onDiscardShare: () -> Void

    var body: some View {
        Group {
            if model.page == .newCase {
                NewCaseView(model: model, onOpened: onOpened, onBack: {
                    let shared = model.fromShare
                    model.closeNewCase()
                    if shared { onDiscardShare() }
                })
            } else {
                FamilyHomeView(model: model, onOpened: onOpened, onSignOut: onSignOut)
            }
        }
        .sheet(isPresented: Binding(
            get: { model.invite != nil },
            set: { if !$0 { model.invite = nil } }
        )) {
            if let invite = model.invite {
                InviteSheet(invite: invite) { model.invite = nil }
            }
        }
        .sheet(isPresented: $model.showAdd) {
            AddChildSheet(model: model)
        }
        .sheet(isPresented: Binding(
            get: { model.callOnlyMemberId != nil },
            set: { if !$0 { model.callOnlyMemberId = nil } }
        )) {
            CallOnlySheet(model: model)
        }
    }
}

struct FamilyHomeView: View {
    @Bindable var model: FamilyModel
    var onOpened: (ParentCase) -> Void
    var onSignOut: () -> Void
    private var locale: AppLocale { AppLocale.resolve() }

    var body: some View {
        Group {
            if model.loading && model.home.children.isEmpty && model.error == nil {
                ProgressView(CopyCatalog.text(.loading, locale))
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .accessibilityIdentifier("family_home")
            } else if let error = model.error, model.home.children.isEmpty {
                VStack(alignment: .leading, spacing: 16) {
                    Banner(text: error)
                    Button(CopyCatalog.text(.actionRetry, locale)) { Task { await model.refresh() } }
                }
                .padding(24)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                .accessibilityIdentifier("family_home")
            } else {
                V3ParentHome(model: model, onOpen: { id in
                    Task { if let item = await model.loadCase(id) { onOpened(item) } }
                }, onSignOut: onSignOut) { action, child in
                    Task { await handle(action, child: child) }
                }
            }
        }
    }

    private func handle(_ action: ChildAction, child: ChildCardState) async {
        switch action {
        case .verify: model.openNewCase(preselect: child.id)
        case .confirmJoin: await model.confirmJoin(memberId: child.id)
        case .rejectJoin: await model.rejectJoin(memberId: child.id)
        case .confirmPhone: await model.confirmPhone(memberId: child.id)
        case .rejectPhone: await model.rejectPhone(memberId: child.id)
        case .reissue: await model.reissue(memberId: child.id)
        case .callOnly:
            model.addPhone = ""
            model.callOnlyMemberId = child.id
        }
    }
}

enum ChildAction { case verify, confirmJoin, rejectJoin, confirmPhone, rejectPhone, reissue, callOnly }

struct ChildCard: View {
    var child: ChildCardState
    var busy: Bool
    var act: (ChildAction) -> Void
    private var locale: AppLocale { AppLocale.resolve() }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(child.name).font(.headline)
            Text(child.statusLine)
            if let request = child.joinRequest {
                Text(request)
                if let hint = child.joinHint { Text(hint).font(.footnote) }
                HStack {
                    Button(CopyCatalog.text(.actionConfirm, locale)) { act(.confirmJoin) }
                        .buttonStyle(.borderedProminent).tint(Theme.accent)
                        .disabled(busy)
                        .accessibilityIdentifier("confirm_\(child.id)")
                    Button(CopyCatalog.text(.actionReject, locale)) { act(.rejectJoin) }
                        .buttonStyle(.bordered).disabled(busy)
                        .accessibilityIdentifier("reject_\(child.id)")
                }
            }
            if let change = child.phoneChange {
                Text(change)
                if let hint = child.phoneChangeHint { Text(hint).font(.footnote) }
                HStack {
                    Button(CopyCatalog.text(.actionConfirm, locale)) { act(.confirmPhone) }
                        .buttonStyle(.borderedProminent).tint(Theme.accent).disabled(busy)
                    Button(CopyCatalog.text(.actionReject, locale)) { act(.rejectPhone) }
                        .buttonStyle(.bordered).disabled(busy)
                }
            }
            if child.canReissue {
                Button(CopyCatalog.text(.childNewInvite, locale)) { act(.reissue) }.disabled(busy)
            }
            if child.canCallOnly {
                Button(CopyCatalog.text(.childAddByPhone, locale)) { act(.callOnly) }.disabled(busy)
            }
            Button(CopyCatalog.text(.actionVerify, locale)) { act(.verify) }
                .buttonStyle(.borderedProminent)
                .tint(Theme.accent)
                .disabled(!child.canVerify || busy)
                .accessibilityIdentifier("verify_\(child.id)")
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(uiColor: .secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .accessibilityIdentifier("child_\(child.id)")
    }
}

struct NewCaseView: View {
    @Bindable var model: FamilyModel
    var onOpened: (ParentCase) -> Void
    var onBack: () -> Void
    private var locale: AppLocale { AppLocale.resolve() }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Button(CopyCatalog.text(.cdBack, locale), action: onBack)
                        .accessibilityIdentifier("back")
                    Text(CopyCatalog.text(.newCaseTitle, locale)).font(.title2)
                }
                Text(CopyCatalog.text(.newCaseNotSentYet, locale))
                    .font(.footnote)
                    .accessibilityIdentifier("not_sent_yet")
                Text(CopyCatalog.text(.newCaseChildHeading, locale)).font(.headline)
                if model.readyChildren.isEmpty {
                    Text(CopyCatalog.text(.newCaseNoChildren, locale))
                } else {
                    ForEach(model.readyChildren) { child in
                        Button {
                            model.caseChildId = child.id
                        } label: {
                            HStack {
                                Image(systemName: model.caseChildId == child.id ? "largecircle.fill.circle" : "circle")
                                Text(child.name)
                                Spacer()
                            }
                        }
                        .accessibilityIdentifier("pick_\(child.id)")
                    }
                }
                Text(CopyCatalog.text(.newCaseTextLabel, locale)).font(.headline)
                TextField(CopyCatalog.text(.newCaseTextHint, locale), text: $model.caseText, axis: .vertical)
                    .lineLimit(4...10)
                    .textFieldStyle(.roundedBorder)
                    .onChange(of: model.caseText) { _, value in
                        if value.count > Limits.text { model.caseText = String(value.prefix(Limits.text)) }
                    }
                    .accessibilityIdentifier("case_text")
                Text(CopyCatalog.text(.newCaseCounter, locale, model.caseText.count, Limits.text))
                    .font(.footnote).foregroundStyle(.secondary)
                if let audio = model.draft {
                    let kilobytes = max(1, Int((audio.sizeBytes + 1023) / 1024))
                    Text(CopyCatalog.text(.newCaseAudioAttached, locale, audio.displayName, kilobytes))
                        .accessibilityIdentifier("draft_audio")
                    Button(CopyCatalog.text(.newCaseAudioRemove, locale)) { model.removeDraft() }
                        .disabled(model.busy)
                        .accessibilityIdentifier("remove_audio")
                }
                Text(CopyCatalog.text(.newCaseExplain, locale))
                if let error = model.error { Banner(text: error) }
                    PrimaryButton(
                    title: model.readyChildren.first { $0.id == model.caseChildId }.map { CopyCatalog.text(.shareAsk, locale, $0.name) } ?? CopyCatalog.text(.newCaseSubmit, locale),
                    identifier: "verify_submit",
                    enabled: !model.busy && model.caseChildId != nil
                ) {
                    Task {
                        if let opened = await model.verify() { onOpened(opened) }
                    }
                }
            }
            .padding(16)
        }
    }
}

struct AddChildSheet: View {
    @Bindable var model: FamilyModel
    private var locale: AppLocale { AppLocale.resolve() }

    var body: some View {
        NavigationStack {
            Form {
                TextField(CopyCatalog.text(.addChildNameLabel, locale), text: $model.addName)
                Toggle(CopyCatalog.text(.addChildModePhone, locale), isOn: $model.addByPhone)
                Text(model.addByPhone
                     ? CopyCatalog.text(.addChildModePhoneHint, locale)
                     : CopyCatalog.text(.addChildModeAppHint, locale))
                    .font(.footnote)
                if model.addByPhone {
                    TextField(CopyCatalog.text(.addChildPhoneLabel, locale), text: $model.addPhone)
                        .keyboardType(.phonePad)
                        .textContentType(.telephoneNumber)
                    Text(CopyCatalog.text(.addChildPhoneExample, locale)).font(.footnote)
                }
                if let error = model.error { Banner(text: error) }
            }
            .navigationTitle(CopyCatalog.text(.addChildTitle, locale))
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(CopyCatalog.text(.actionCancel, locale)) { model.showAdd = false }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(CopyCatalog.text(.addChildSubmit, locale)) { Task { await model.addChild() } }
                        .disabled(model.busy)
                }
            }
        }
        .presentationDetents([.medium, .large])
    }
}

struct CallOnlySheet: View {
    @Bindable var model: FamilyModel
    private var locale: AppLocale { AppLocale.resolve() }
    private var name: String {
        model.home.children.first { $0.id == model.callOnlyMemberId }?.name ?? ""
    }

    var body: some View {
        NavigationStack {
            Form {
                Text(CopyCatalog.text(.addChildModePhoneHint, locale)).font(.footnote)
                TextField(CopyCatalog.text(.addChildPhoneLabel, locale), text: $model.addPhone)
                    .keyboardType(.phonePad)
                if let error = model.error { Banner(text: error) }
            }
            .navigationTitle(CopyCatalog.text(.callOnlyTitle, locale, name))
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(CopyCatalog.text(.actionCancel, locale)) { model.callOnlyMemberId = nil }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(CopyCatalog.text(.callOnlySubmit, locale)) { Task { await model.submitCallOnly() } }
                        .disabled(model.busy)
                }
            }
        }
        .presentationDetents([.medium])
    }
}

struct InviteSheet: View {
    var invite: ShownInvite
    var onDone: () -> Void
    @State private var copied = false
    private var locale: AppLocale { AppLocale.resolve() }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                Text(CopyCatalog.text(.inviteTitle, locale, invite.name)).font(.title2)
                Text(CopyCatalog.text(.inviteBody, locale, invite.name))
                Text(invite.secret)
                    .font(.title.monospaced())
                    .textSelection(.enabled)
                    .accessibilityIdentifier("invite_secret")
                let expires = Times.shortDateTime(invite.expiresAt, locale: .current)
                if !expires.isEmpty {
                    Text(CopyCatalog.text(.inviteExpires, locale, expires))
                }
                Button(copied ? CopyCatalog.text(.copied, locale) : CopyCatalog.text(.actionCopy, locale)) {
                    Pasteboard.copy(invite.secret, expiresAfter: 60)
                    copied = true
                }
                .accessibilityIdentifier("invite_copy")
                Button(CopyCatalog.text(.actionShare, locale)) {
                    ShareSheet.present(CopyCatalog.text(.inviteShareText, locale, invite.secret))
                }
                Spacer()
            }
            .padding(24)
            .navigationTitle(CopyCatalog.text(.inviteTitle, locale, invite.name))
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button(CopyCatalog.text(.actionDone, locale), action: onDone)
                }
            }
        }
    }
}
