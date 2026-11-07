import FamilyShieldCore
import SwiftUI
import UIKit

struct RootView: View {
    @Bindable var model: AppModel

    var body: some View {
        Group {
            if let fixture = AppModel.uiTestFixture() {
                UITestHost(fixture: fixture)
            } else {
                live
            }
        }
        .tint(Theme.accent)
        .task { await model.start() }
    }

    @ViewBuilder private var live: some View {
        switch model.phase {
        case .loading:
            ProgressView(CopyCatalog.text(.loading, AppLocale.resolve()))
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        case .signedOut:
            SignInView(model: model)
        case .needsFamily:
            CreateFamilyView(model: model)
        case .parent(let familyId, let familyName):
            ParentHost(app: model, familyId: familyId, familyName: familyName)
        case .childPlaceholder:
            MessageScreen(
                title: CopyCatalog.text(.childPlaceholderTitle, AppLocale.resolve()),
                message: CopyCatalog.text(.childPlaceholderBody, AppLocale.resolve()),
                onSignOut: model.signOut
            )
        case .membershipPending:
            MessageScreen(
                title: CopyCatalog.text(.membershipPendingTitle, AppLocale.resolve()),
                message: CopyCatalog.text(.membershipPendingBody, AppLocale.resolve()),
                onSignOut: model.signOut
            )
        case .failed(let message):
            VStack(alignment: .leading, spacing: 16) {
                Text(CopyCatalog.text(.rootErrorTitle, AppLocale.resolve())).font(.title2)
                Text(message)
                PrimaryButton(title: CopyCatalog.text(.actionRetry, AppLocale.resolve()), identifier: "retry") {
                    Task { await model.reload() }
                }
            }
            .padding(24)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
    }

}

struct ParentHost: View {
    var app: AppModel
    var familyId: String
    var familyName: String
    @State private var family: FamilyModel?

    var body: some View {
        Group {
            if let open = app.openCase {
                CaseScreen(item: open, api: app.api, onBack: { app.openCase = nil })
            } else if let family {
                FamilyFlow(model: family) { opened in
                    app.openCase = opened
                } onSignOut: {
                    app.signOut()
                }
            } else {
                ProgressView(CopyCatalog.text(.loading, AppLocale.resolve()))
            }
        }
        .task(id: familyId) {
            if family == nil {
                family = FamilyModel(familyId: familyId, familyName: familyName, api: app.api)
            }
            await family?.refresh()
        }
    }
}

struct MessageScreen: View {
    var title: String
    var message: String
    var onSignOut: () -> Void
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(title).font(.title2)
            Text(message)
            PrimaryButton(title: CopyCatalog.text(.actionSignOut, AppLocale.resolve()), identifier: "sign_out", action: onSignOut)
        }
        .padding(24)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}

enum Pasteboard {
    static func copy(_ text: String, expiresAfter seconds: TimeInterval) {
        UIPasteboard.general.setItems(
            [[UIPasteboard.typeAutomatic: text]],
            options: [
                .localOnly: true,
                .expirationDate: Date().addingTimeInterval(seconds),
            ]
        )
    }
}

enum ShareSheet {
    static func present(_ text: String) {
        let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
        let root = scenes.flatMap(\.windows).first { $0.isKeyWindow }?.rootViewController
        let controller = UIActivityViewController(activityItems: [text], applicationActivities: nil)
        root?.present(controller, animated: true)
    }
}
