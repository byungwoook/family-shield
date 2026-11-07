import FamilyShieldCore
import Foundation
import Observation
import UserNotifications

@MainActor
final class AppRuntime {
    static let shared = AppRuntime()
    weak var model: AppModel?
    func notePushToken(_ token: String) {
        model?.notePushToken(token)
    }
}

@MainActor
@Observable
final class AppModel {
    enum Phase: Equatable {
        case loading
        case signedOut
        case needsFamily
        case parent(familyId: String, familyName: String)
        case child(ChildDestination)
        case membershipPending
        case failed(String)
    }

    private(set) var phase: Phase = .loading
    var openCase: ParentCase?
    let session: KeychainTokenStore
    let api: APIClient
    private var pushToken: String?
    private var started = false
    var share: ShareMarker?
    var shareDirectory: URL?
    var childCaseId: String?

    init() {
        let session = KeychainTokenStore()
        session.load()
        let hook = SignOutHook()
        self.session = session
        self.api = APIClient(baseURL: APIBase.current, tokens: session) { token in
            hook.fire(token)
        }
        hook.fire = { [weak self] _ in
            Task { @MainActor in
                self?.forceSignOut()
            }
        }
    }

    func start() async {
        if let fixture = Self.uiTestFixture() {
            phase = .signedOut
            openCase = nil
            return
        }
        guard !started else { return }
        started = true
        AppRuntime.shared.model = self
        UNUserNotificationCenter.current().delegate = PushCenter.shared
        refreshShare()
        await reload()
    }

    func refreshShare() {
        guard let container = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: AppGroupID.identifier) else { return }
        let directory = container.appendingPathComponent("share-drafts", isDirectory: true)
        shareDirectory = directory
        share = ShareDrafts.readMarker(directory: directory)
    }

    func openChildCase(_ id: String) {
        guard ChildRules.isCaseId(id) else { return }
        childCaseId = id
    }

    func discardShare() {
        if let shareDirectory { ShareDrafts.wipe(shareDirectory) }
        share = nil
    }

    static func uiTestFixture() -> ParentFixture? {
        let args = ProcessInfo.processInfo.arguments
        guard let index = args.firstIndex(of: "--ui-test"), args.indices.contains(index + 1) else { return nil }
        return ParentFixture(rawValue: args[index + 1])
    }

    func reload() async {
        guard session.currentToken() != nil else {
            phase = .signedOut
            openCase = nil
            return
        }
        phase = .loading
        do {
            apply(try await api.me())
            await registerPushIfPossible()
        } catch let error as APIError {
            if case .http(let status, _) = error, status == 401 { return }
            phase = .failed(CopyCatalog.text(ErrorCopy.key(for: error), AppLocale.resolve()))
        } catch {
            phase = .failed(CopyCatalog.text(.errorGeneric, AppLocale.resolve()))
        }
    }

    func completeAppleSignIn(idToken: String, rawNonce: String, displayName: String?) async -> String? {
        do {
            let session = try await api.signInWithApple(
                idToken: idToken,
                rawNonce: rawNonce,
                locale: AppLocale.resolve().rawValue,
                displayName: displayName
            )
            self.session.save(session.token)
            PushRegistration.requestAndRegister()
            await reload()
            return nil
        } catch let error as APIError {
            return CopyCatalog.text(ErrorCopy.key(for: error), AppLocale.resolve())
        } catch {
            return CopyCatalog.text(.errorAppleFailed, AppLocale.resolve())
        }
    }

    #if DEV_LOGIN
    func devSignIn(name: String) async -> String? {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return CopyCatalog.text(.errorNameRequired, AppLocale.resolve()) }
        do {
            let session = try await api.devLogin(displayName: String(trimmed.prefix(Limits.name)), locale: AppLocale.resolve().rawValue)
            self.session.save(session.token)
            PushRegistration.requestAndRegister()
            await reload()
            return nil
        } catch let error as APIError {
            return CopyCatalog.text(ErrorCopy.key(for: error), AppLocale.resolve())
        } catch {
            return CopyCatalog.text(.errorGeneric, AppLocale.resolve())
        }
    }
    #endif

    func familyCreated(_ family: FamilyCreated) {
        phase = .parent(familyId: family.id, familyName: family.name)
    }

    func signOut() {
        forceSignOut()
    }

    func notePushToken(_ token: String) {
        pushToken = token
        Task { await registerPushIfPossible() }
    }

    private func forceSignOut() {
        session.clear()
        openCase = nil
        phase = .signedOut
    }

    private func apply(_ me: Me) {
        switch SessionRoute.destination(for: me) {
        case .needsFamily:
            phase = .needsFamily
        case .parent(let familyId, let familyName):
            phase = .parent(familyId: familyId, familyName: familyName)
        case .child(let child):
            phase = .child(child)
        case .membershipPending:
            phase = .membershipPending
        }
        PushRegistration.requestAndRegister()
    }

    private func registerPushIfPossible() async {
        guard let pushToken, session.currentToken() != nil else { return }
        #if DEBUG
        let env = "sandbox"
        #else
        let env = "production"
        #endif
        do {
            _ = try await api.registerPushToken(token: pushToken, env: env, locale: AppLocale.resolve().rawValue)
        } catch {
            // A failed registration must not block the parent. The token is not logged.
        }
    }
}
