import AuthenticationServices
import FamilyShieldCore
import SwiftUI

struct SignInView: View {
    var model: AppModel
    @State private var busy = false
    @State private var error: String?
    @State private var rawNonce: String?
    #if DEV_LOGIN
    @State private var devName = ""
    #endif

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(CopyCatalog.text(.appName, AppLocale.resolve()))
                    .font(.largeTitle).bold()
                    .padding(.top, 24)
                Text(CopyCatalog.text(.signinTagline, AppLocale.resolve()))
                    .font(.title3)
                Text(CopyCatalog.text(.signinPromise, AppLocale.resolve()))
                Text(CopyCatalog.text(.signinPrivacy, AppLocale.resolve()))
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                SignInWithAppleButton(.signIn) { request in
                    request.requestedScopes = [.fullName]
                    request.nonce = Nonces.sha256Hex(rawNonce ?? "")
                } onCompletion: { result in
                    Task { await finishApple(result) }
                }
                .signInWithAppleButtonStyle(.black)
                .frame(maxWidth: .infinity, minHeight: 44)
                .disabled(busy || rawNonce == nil)
                .accessibilityIdentifier("apple_sign_in")
                #if DEV_LOGIN
                Divider()
                Text(DevCopy.heading)
                    .font(.headline)
                    .accessibilityIdentifier("dev_heading")
                TextField(DevCopy.name, text: $devName)
                    .textFieldStyle(.roundedBorder)
                    .textContentType(.name)
                    .accessibilityIdentifier("dev_name")
                Button(DevCopy.button) {
                    Task {
                        busy = true
                        error = await model.devSignIn(name: devName)
                        busy = false
                    }
                }
                .buttonStyle(.bordered)
                .controlSize(.large)
                .frame(maxWidth: .infinity)
                .disabled(busy)
                .accessibilityIdentifier("dev_sign_in")
                #endif
                if let error { Banner(text: error) }
            }
            .padding(24)
        }
        .task { await prepareNonce() }
    }

    private func prepareNonce() async {
        do {
            rawNonce = try await model.api.nonce().nonce
        } catch let failure as APIError {
            error = CopyCatalog.text(ErrorCopy.key(for: failure), AppLocale.resolve())
        } catch {
            self.error = CopyCatalog.text(.errorGeneric, AppLocale.resolve())
        }
    }

    private func finishApple(_ result: Result<ASAuthorization, Error>) async {
        guard let rawNonce else { return }
        busy = true
        defer { busy = false }
        switch result {
        case .failure(let failure):
            let cancelled = (failure as? ASAuthorizationError)?.code == .canceled
            if !cancelled { error = CopyCatalog.text(.errorAppleFailed, AppLocale.resolve()) }
            await prepareNonce()
        case .success(let authorization):
            guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
                  let tokenData = credential.identityToken,
                  let token = String(data: tokenData, encoding: .utf8)
            else {
                error = CopyCatalog.text(.errorAppleFailed, AppLocale.resolve())
                await prepareNonce()
                return
            }
            let name = [credential.fullName?.givenName, credential.fullName?.familyName]
                .compactMap { $0?.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { !$0.isEmpty }
                .joined(separator: " ")
            error = await model.completeAppleSignIn(idToken: token, rawNonce: rawNonce, displayName: name.isEmpty ? nil : name)
            self.rawNonce = nil
            if error != nil { await prepareNonce() }
        }
    }
}

#if DEV_LOGIN
enum DevCopy {
    static var heading: String {
        AppLocale.resolve() == .ko ? "개발자 로그인 (디버그 빌드 전용)" : "Developer sign-in (debug build only)"
    }
    static var name: String { AppLocale.resolve() == .ko ? "이름" : "Your name" }
    static var button: String { AppLocale.resolve() == .ko ? "개발자로 로그인" : "Sign in as developer" }
}
#endif

struct CreateFamilyView: View {
    var model: AppModel
    @State private var name = ""
    @State private var busy = false
    @State private var error: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(CopyCatalog.text(.createFamilyTitle, AppLocale.resolve())).font(.title2)
                Text(CopyCatalog.text(.createFamilyBody, AppLocale.resolve()))
                TextField(CopyCatalog.text(.createFamilyNameLabel, AppLocale.resolve()), text: $name)
                    .textFieldStyle(.roundedBorder)
                    .accessibilityIdentifier("family_name")
                PrimaryButton(
                    title: CopyCatalog.text(.createFamilyButton, AppLocale.resolve()),
                    identifier: "create_family",
                    enabled: !busy
                ) {
                    Task { await create() }
                }
                Button(CopyCatalog.text(.actionSignOut, AppLocale.resolve()), action: model.signOut)
                    .accessibilityIdentifier("sign_out")
                if let error { Banner(text: error) }
            }
            .padding(24)
        }
    }

    private func create() async {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            error = CopyCatalog.text(.errorNameRequired, AppLocale.resolve())
            return
        }
        busy = true
        error = nil
        do {
            let family = try await model.api.createFamily(name: String(trimmed.prefix(Limits.name)))
            model.familyCreated(family)
        } catch let failure as APIError {
            error = CopyCatalog.text(ErrorCopy.key(for: failure), AppLocale.resolve())
        } catch {
            self.error = CopyCatalog.text(.errorGeneric, AppLocale.resolve())
        }
        busy = false
    }
}
