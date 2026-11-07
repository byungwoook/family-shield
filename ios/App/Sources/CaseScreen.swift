import FamilyShieldCore
import SwiftUI

struct CaseScreen: View {
    var api: APIClient
    var onBack: () -> Void
    @State private var current: ParentCase
    @State private var updateFailed = false
    @Environment(\.colorScheme) private var scheme
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
        let view = presentation
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Button(CopyCatalog.text(.cdBack, locale), action: onBack)
                        .accessibilityIdentifier("back")
                    Text(CopyCatalog.text(.caseTitle, locale, view.name)).font(.title2)
                }
                if let dont = view.dontSend {
                    Text(dont).font(.title3).bold()
                        .accessibilityIdentifier("dont_send")
                }
                if let line = view.openLine { Text(line) }
                if !view.title.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(view.title).font(.title2).accessibilityIdentifier("result_title")
                        Text(view.body).accessibilityIdentifier("result_body")
                        if let checked = view.checkedAt { Text(checked).font(.footnote) }
                    }
                    .padding(16)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Theme.background(view.color, scheme: scheme))
                    .foregroundStyle(Theme.foreground(view.color, scheme: scheme))
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .accessibilityElement(children: .contain)
                    .accessibilityIdentifier("result_card")
                }
                if let pattern = view.patternLine { Text(pattern) }
                if let alert = view.familyAlert {
                    Text(CopyCatalog.text(.familyAlertHeading, locale)).font(.headline)
                    Text(CopyCatalog.text(.familyAlertLead, locale))
                    Text(alert).accessibilityIdentifier("family_alert")
                    Button(copied ? CopyCatalog.text(.copied, locale) : CopyCatalog.text(.actionCopy, locale)) {
                        Pasteboard.copy(alert, expiresAfter: 600)
                        copied = true
                    }
                    .accessibilityIdentifier("alert_copy")
                    Button(CopyCatalog.text(.actionShare, locale)) { ShareSheet.present(alert) }
                }
                if let heading = view.claimsHeading {
                    Text(heading).font(.headline)
                    ForEach(Array(view.claimLines.enumerated()), id: \.offset) { _, line in Text(line) }
                }
                if let heading = view.parentTextHeading, let text = view.parentText {
                    Text(heading).font(.headline)
                    Text(text)
                }
                if let heading = view.timelineHeading {
                    Text(heading).font(.headline)
                    ForEach(Array(view.timeline.enumerated()), id: \.offset) { _, step in
                        Text("• \(step)")
                    }
                }
                if let failed = view.updateFailed { Banner(text: failed) }
            }
            .padding(16)
        }
        .accessibilityIdentifier("case_screen")
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
        if let home = ParentFixtures.home(fixture, locale: locale, now: now) {
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
