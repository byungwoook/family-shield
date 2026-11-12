import FamilyShieldCore
import SwiftUI

struct CaseScreen: View {
    var api: APIClient
    var onBack: () -> Void
    @State private var current: ParentCase
    @State private var updateFailed = false
    @State private var copied = false

    init(item: ParentCase, api: APIClient, onBack: @escaping () -> Void) {
        self.api = api
        self.onBack = onBack
        _current = State(initialValue: item)
    }

    private var locale: AppLocale { AppLocale.resolve() }
    private var presentation: CasePresentation {
        CasePresenter.present(current, locale: locale, formattingLocale: .current, updateFailed: updateFailed)
    }

    var body: some View {
        V3CaseBody(
            item: current,
            view: presentation,
            onBack: onBack,
            onCopy: { text in
                Pasteboard.copy(text, expiresAfter: 600)
                copied = true
            },
            onShare: { ShareSheet.present($0) }
        )
        .task { await poll() }
    }

    private func poll() async {
        while !Task.isCancelled {
            if CaseColor.of(current.color, decidedAt: current.decidedAt).isDecided { return }
            do {
                let fresh = try await api.parentCase(caseId: current.id)
                switch CasePolling.outcome(.success(fresh)) {
                case .decided(let item):
                    current = item
                    updateFailed = false
                    return
                case .open(let item):
                    current = item
                    updateFailed = false
                case .unauthorized:
                    return
                case .failedKeepWaiting:
                    updateFailed = true
                }
            } catch let error as APIError {
                switch CasePolling.outcome(.failure(error)) {
                case .unauthorized: return
                default: updateFailed = true
                }
            } catch {
                updateFailed = true
            }
            try? await Task.sleep(nanoseconds: 3_000_000_000)
        }
    }
}

struct UITestHost: View {
    var fixture: ParentFixture
    @Environment(\.colorScheme) private var scheme

    var body: some View {
        let locale = AppLocale.resolve()
        let now = Times.parse("2026-11-07T12:00:00+00:00") ?? Date()
        if fixture == .notNow {
            NotNowFixture()
        } else if fixture == .resetLocked {
            VStack(alignment: .leading, spacing: 12) {
                Text(CopyCatalog.text(.childResetBody, locale))
                Text(CopyCatalog.text(.biometricSubtitle, locale))
                Button(CopyCatalog.text(.childResetUnlock, locale)) {}
                    .accessibilityIdentifier("reset_unlock")
            }
            .padding(16)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .accessibilityIdentifier("reset_locked")
        } else if fixture == .shareDraft {
            VStack(alignment: .leading, spacing: 12) {
                Text(CopyCatalog.text(.newCaseNotSentYet, locale))
                    .accessibilityIdentifier("not_sent_yet")
                Text(CopyCatalog.text(.newCaseAudioAttached, locale, "voice.m4a", 1))
                    .accessibilityIdentifier("draft_audio")
            }
            .padding(16)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        } else if let home = ParentFixtures.home(fixture, locale: locale, now: now) {
            FixtureHome(home: home)
        } else if let item = ParentFixtures.caseItem(fixture) {
            let view = CasePresenter.present(item, locale: locale, formattingLocale: .current)
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text(CopyCatalog.text(.caseTitle, locale, view.name)).font(.title2)
                    Text(view.title).font(.title2).accessibilityIdentifier("result_title")
                    Text(view.body).accessibilityIdentifier("result_body")
                    if let pattern = view.patternLine { Text(pattern) }
                    if let alert = view.familyAlert {
                        Text(CopyCatalog.text(.familyAlertHeading, locale)).font(.headline)
                        Text(alert).accessibilityIdentifier("family_alert")
                    }
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .background(Theme.background(view.color, scheme: scheme).opacity(0.35))
            .accessibilityIdentifier("case_screen")
        }
    }
}

private struct NotNowFixture: View {
    @State private var prompt = ChildPrompt(prompt: true, caseState: "waiting_push")
    private var locale: AppLocale { AppLocale.resolve() }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if prompt.prompt {
                Text(CopyCatalog.text(.childQuestion, locale)).accessibilityIdentifier("child_question")
                Button(CopyCatalog.text(.childNotNow, locale)) {
                    prompt = ChildDecisions.notNow(prompt).0
                }
                .accessibilityIdentifier("not_now")
            } else {
                Text(CopyCatalog.text(.childQuestionHint, locale)).accessibilityIdentifier("still_open")
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}

private struct FixtureHome: View {
    var home: FamilyHomeState
    private var locale: AppLocale { AppLocale.resolve() }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(home.familyName).font(.title2)
                Text(CopyCatalog.text(.familyChildrenHeading, locale)).font(.headline)
                if home.isEmpty {
                    Text(CopyCatalog.text(.familyEmptyTitle, locale))
                        .font(.title3)
                        .accessibilityIdentifier("family_empty")
                    Text(CopyCatalog.text(.familyEmptyBody, locale))
                } else {
                    ForEach(home.children) { child in
                        VStack(alignment: .leading, spacing: 8) {
                            Text(child.name).font(.headline)
                            Text(child.statusLine)
                            if let request = child.joinRequest { Text(request) }
                            Button(CopyCatalog.text(.actionVerify, locale)) {}
                                .buttonStyle(.borderedProminent)
                                .disabled(!child.canVerify)
                                .accessibilityIdentifier("verify_\(child.id)")
                        }
                        .padding(16)
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
            }
            .padding(16)
        }
        .accessibilityIdentifier("family_home")
    }
}
