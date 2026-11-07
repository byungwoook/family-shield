import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// A voice note already stored on the phone. Building this does not upload it.
public struct CaseAudio: Sendable {
    public var fileURL: URL
    public var uploadName: String
    public var contentType: String
    public init(fileURL: URL, uploadName: String, contentType: String) {
        self.fileURL = fileURL
        self.uploadName = uploadName
        self.contentType = contentType
    }
}

enum Multipart {
    static func body(fields: [String: String], fileField: String, fileName: String, contentType: String, file: Data) -> (Data, String) {
        let boundary = "FamilyShield\(UUID().uuidString.replacingOccurrences(of: "-", with: ""))"
        var data = Data()
        func append(_ string: String) { data.append(Data(string.utf8)) }
        for (key, value) in fields.sorted(by: { $0.key < $1.key }) {
            append("--\(boundary)\r\n")
            append("Content-Disposition: form-data; name=\"\(key)\"\r\n\r\n")
            append(value)
            append("\r\n")
        }
        append("--\(boundary)\r\n")
        append("Content-Disposition: form-data; name=\"\(fileField)\"; filename=\"\(fileName)\"\r\n")
        append("Content-Type: \(contentType)\r\n\r\n")
        data.append(file)
        append("\r\n--\(boundary)--\r\n")
        return (data, boundary)
    }
}

public enum APIError: Error, Equatable, Sendable {
    case notConfigured
    case network
    case decode
    /// `code` is the `error` field, or `http_<status>` when the body had none.
    case http(status: Int, code: String)
}

public struct HTTPResponse: Sendable, Equatable {
    public var status: Int
    public var body: Data
    public init(status: Int, body: Data) {
        self.status = status
        self.body = body
    }
}

public protocol HTTPTransport: Sendable {
    func perform(_ request: URLRequest) async throws -> HTTPResponse
}

public struct URLSessionTransport: HTTPTransport {
    public init() {}
    public func perform(_ request: URLRequest) async throws -> HTTPResponse {
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw URLError(.badServerResponse) }
        return HTTPResponse(status: http.statusCode, body: data)
    }
}

public protocol TokenProviding: Sendable {
    func currentToken() -> String?
}

/// The only HTTP client. It adds `Authorization: Bearer`, maps `{"error": code}`
/// to `APIError.http`, and reports a 401 so the session can sign out.
/// Nothing here logs: bodies carry names, invite secrets, and session tokens.
public final class APIClient: Sendable {
    private let base: URL?
    private let tokens: TokenProviding
    private let transport: HTTPTransport
    private let onUnauthorized: @Sendable (String) -> Void

    public var isConfigured: Bool { base != nil }

    public init(
        baseURL: String,
        tokens: TokenProviding,
        transport: HTTPTransport = URLSessionTransport(),
        onUnauthorized: @escaping @Sendable (String) -> Void = { _ in }
    ) {
        let trimmed = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        if let url = URL(string: trimmed), let scheme = url.scheme, scheme == "http" || scheme == "https", url.host != nil {
            self.base = url
        } else {
            self.base = nil
        }
        self.tokens = tokens
        self.transport = transport
        self.onUnauthorized = onUnauthorized
    }

    // MARK: Auth

    public func nonce() async throws -> NonceResponse {
        try await postEmpty("v1", "auth", "nonce", auth: false)
    }

    public func signInWithApple(idToken: String, rawNonce: String, locale: String, displayName: String?) async throws -> SessionResponse {
        var fields: [String: String] = ["id_token": idToken, "nonce": rawNonce, "locale": locale]
        let name = displayName?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if !name.isEmpty {
            fields["display_name"] = String(name.prefix(Limits.name))
        }
        return try await postJSON(fields, "v1", "auth", "apple", auth: false)
    }

    public func devLogin(displayName: String, locale: String, authSubject: String? = nil) async throws -> DevLoginResponse {
        var fields = ["display_name": displayName, "locale": locale]
        if let authSubject, !authSubject.isEmpty { fields["auth_subject"] = authSubject }
        return try await postJSON(fields, "v1", "dev", "login", auth: false)
    }

    // MARK: Parent

    public func me() async throws -> Me { try await get("v1", "me") }

    public func createFamily(name: String) async throws -> FamilyCreated {
        try await postJSON(["name": name], "v1", "families")
    }

    public func addChild(familyId: String, displayName: String) async throws -> ChildInvite {
        try await postJSON(["display_name": displayName], "v1", "families", familyId, "children")
    }

    public func members(familyId: String) async throws -> Roster {
        try await get("v1", "families", familyId, "members")
    }

    public func familyCases(familyId: String, limit: Int = 20) async throws -> CaseList {
        try await get("v1", "families", familyId, "cases", query: ["limit": String(limit)])
    }

    public func reissueInvite(familyId: String, memberId: String) async throws -> InviteReissued {
        try await postEmpty("v1", "families", familyId, "members", memberId, "invite")
    }

    public func confirmMember(familyId: String, memberId: String, decision: ParentDecision) async throws -> MemberDecision {
        try await postJSON(["decision": decision.rawValue], "v1", "families", familyId, "members", memberId, "confirm")
    }

    public func decidePhoneChange(familyId: String, memberId: String, decision: ParentDecision) async throws -> PhoneChangeDecision {
        try await postJSON(["decision": decision.rawValue], "v1", "families", familyId, "members", memberId, "phone-change")
    }

    public func addCallOnly(familyId: String, memberId: String, phoneE164: String) async throws -> LinkSent {
        try await postJSON(["phone_e164": phoneE164], "v1", "families", familyId, "members", memberId, "call-only")
    }

    public func sendAllowLink(familyId: String, memberId: String) async throws -> LinkSent {
        try await postEmpty("v1", "families", familyId, "members", memberId, "allow-link")
    }

    /// Opens a case. With `audio`, the body is multipart and `Content-Length`
    /// is set. Without it, the body stays JSON. Either way this runs only when
    /// the parent taps Verify.
    public func openCase(childMemberId: String, text: String, audio: CaseAudio? = nil) async throws -> ParentCase {
        let clipped = String(text.prefix(Limits.text))
        guard let audio else {
            return try await postJSON(["child_member_id": childMemberId, "text": clipped], "v1", "cases")
        }
        try rejectUnusable(audio)
        let file = try Data(contentsOf: audio.fileURL)
        let (body, boundary) = Multipart.body(
            fields: ["child_member_id": childMemberId, "text": clipped],
            fileField: "audio",
            fileName: VoiceNotes.uploadName(displayName: audio.uploadName, contentType: audio.contentType),
            contentType: audio.contentType,
            file: file
        )
        let data = try await send(
            method: "POST",
            parts: ["v1", "cases"],
            query: [:],
            body: body,
            contentType: "multipart/form-data; boundary=\(boundary)",
            auth: true,
            contentLength: body.count
        )
        return try JSONCoding.decode(ParentCase.self, from: data)
    }

    public func parentCase(caseId: String) async throws -> ParentCase {
        try await get("v1", "cases", caseId)
    }

    public func acceptInvite(secret: String) async throws -> InviteAccepted {
        try await postJSON(["secret": ChildRules.normalizeInvite(secret)], "v1", "invites", "accept")
    }

    public func startOtp(phoneE164: String, channel: String, biometricOk: Bool) async throws -> OtpStarted {
        let body = try JSONSerialization.data(withJSONObject: [
            "phone_e164": phoneE164,
            "channel": channel,
            "biometric_ok": biometricOk,
        ] as [String: Any], options: [.sortedKeys])
        let data = try await send(method: "POST", parts: ["v1", "phones", "otp"], query: [:], body: body, contentType: "application/json; charset=utf-8", auth: true)
        return try JSONCoding.decode(OtpStarted.self, from: data)
    }

    public func checkOtp(phoneE164: String, code: String) async throws -> OtpChecked {
        try await postJSON(["phone_e164": phoneE164, "code": code], "v1", "phones", "otp", "check")
    }

    public func setCheckCode(_ code: String, biometricOk: Bool) async throws -> StatusBody {
        let body = try JSONSerialization.data(withJSONObject: ["code": code, "biometric_ok": biometricOk] as [String: Any], options: [.sortedKeys])
        let data = try await send(method: "POST", parts: ["v1", "me", "check-code"], query: [:], body: body, contentType: "application/json; charset=utf-8", auth: true)
        return try JSONCoding.decode(StatusBody.self, from: data)
    }

    public func childCase(caseId: String) async throws -> ChildCase {
        try await get("v1", "cases", caseId)
    }

    public func answerCase(caseId: String, answer: String) async throws -> ChildCase {
        try await postJSON(["answer": answer], "v1", "cases", caseId, "answer")
    }

    public func callCode(caseId: String) async throws -> CallCode {
        try await get("v1", "cases", caseId, "call-code")
    }

    public func registerPushToken(token: String, env: String, locale: String) async throws -> PushRegistration {
        try await postJSON(
            ["provider": "apns", "token": token, "env": env, "locale": locale],
            "v1", "me", "push-token"
        )
    }

    // MARK: Transport

    private func get<T: Decodable>(_ parts: String..., query: [String: String] = [:]) async throws -> T {
        let data = try await send(method: "GET", parts: parts, query: query, body: nil, contentType: nil, auth: true)
        return try JSONCoding.decode(T.self, from: data)
    }

    private func postJSON<T: Decodable>(_ fields: [String: String], _ parts: String..., auth: Bool = true) async throws -> T {
        let body = try JSONSerialization.data(withJSONObject: fields, options: [.sortedKeys])
        let data = try await send(method: "POST", parts: parts, query: [:], body: body, contentType: "application/json; charset=utf-8", auth: auth)
        return try JSONCoding.decode(T.self, from: data)
    }

    private func postEmpty<T: Decodable>(_ parts: String..., auth: Bool = true) async throws -> T {
        let data = try await send(method: "POST", parts: parts, query: [:], body: Data(), contentType: nil, auth: auth)
        return try JSONCoding.decode(T.self, from: data)
    }

    private func rejectUnusable(_ audio: CaseAudio) throws {
        let type = audio.contentType.lowercased()
        let audioType = try NSRegularExpression(pattern: "^audio/[a-z0-9.+-]+$")
        let range = NSRange(type.startIndex..., in: type)
        if audioType.firstMatch(in: type, range: range) == nil {
            throw APIError.http(status: 415, code: "unsupported_audio")
        }
        let size = Int64((try? audio.fileURL.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? -1)
        if size <= 0 { throw APIError.http(status: 400, code: "empty_audio") }
        if size > VoiceNotes.maxBytes { throw APIError.http(status: 413, code: "audio_too_large") }
    }

    private func send(method: String, parts: [String], query: [String: String], body: Data?, contentType: String?, auth: Bool, contentLength: Int? = nil) async throws -> Data {
        guard let url = url(parts, query: query) else { throw APIError.notConfigured }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 30
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let contentType { request.setValue(contentType, forHTTPHeaderField: "Content-Type") }
        if let contentLength { request.setValue(String(contentLength), forHTTPHeaderField: "Content-Length") }
        request.httpBody = body
        let token = auth ? tokens.currentToken()?.trimmingCharacters(in: .whitespacesAndNewlines) : nil
        if auth {
            guard let token, !token.isEmpty else { throw APIError.http(status: 401, code: "unauthorized") }
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let response: HTTPResponse
        do {
            response = try await transport.perform(request)
        } catch {
            throw APIError.network
        }
        if !(200...299).contains(response.status) {
            if response.status == 401, let token { onUnauthorized(token) }
            throw APIError.http(status: response.status, code: errorCode(response.body) ?? "http_\(response.status)")
        }
        return response.body
    }

    private func url(_ parts: [String], query: [String: String]) -> URL? {
        guard let base else { return nil }
        guard var components = URLComponents(url: base, resolvingAgainstBaseURL: false) else { return nil }
        var path = components.path
        if path.hasSuffix("/") { path.removeLast() }
        for part in parts {
            let encoded = part.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? part
            path += "/" + encoded
        }
        components.path = path
        if !query.isEmpty {
            components.queryItems = query.keys.sorted().map { URLQueryItem(name: $0, value: query[$0]) }
        }
        return components.url
    }

    private func errorCode(_ body: Data) -> String? {
        guard let object = try? JSONSerialization.jsonObject(with: body) as? [String: Any] else { return nil }
        guard let code = object["error"] as? String, !code.isEmpty else { return nil }
        return code
    }
}

public enum ErrorCopy {
    public static func key(for error: APIError) -> CopyKey {
        switch error {
        case .network: return .errorNetwork
        case .notConfigured: return .errorNotConfigured
        case .decode: return .errorDecode
        case .http(let status, let code): return key(status: status, code: code)
        }
    }

    public static func key(status: Int, code: String) -> CopyKey {
        switch code {
        case "unauthorized": return .errorUnauthorized
        case "invalid_token": return .errorInvalidToken
        case "sign_in_unavailable": return .errorSignInUnavailable
        case "invalid_body": return .errorInvalidBody
        case "not_found": return .errorNotFound
        case "not_a_parent": return .errorNotAParent
        case "already_in_a_family": return .errorAlreadyInAFamily
        case "invite_not_open": return .errorInviteNotOpen
        case "member_not_pending": return .errorMemberNotPending
        case "member_not_ready": return .errorMemberNotReady
        case "no_pending_number": return .errorNoPendingNumber
        case "phone_in_use": return .errorPhoneInUse
        case "invalid_phone": return .errorInvalidPhone
        case "unsupported_country": return .errorUnsupportedCountry
        case "not_call_only": return .errorNotCallOnly
        case "otp_unavailable", "allow_link_unavailable": return .errorSmsUnavailable
        case "sms_failed": return .errorSmsFailed
        case "member_not_callable": return .errorMemberNotCallable
        case "rate_limited": return .errorRateLimited
        case "audio_too_large": return .errorAudioTooLarge
        case "unsupported_audio": return .errorUnsupportedAudio
        case "empty_audio": return .errorEmptyAudio
        case "length_required": return .errorLengthRequired
        case "invite_invalid": return .errorInviteInvalid
        case "invite_expired": return .errorInviteExpired
        case "not_a_child": return .errorNotAChild
        case "biometric_required": return .errorBiometricRequired
        case "phone_already_set": return .errorPhoneAlreadySet
        case "same_number": return .errorSameNumber
        case "otp_wrong": return .errorOtpWrong
        case "otp_expired": return .errorOtpExpired
        case "invalid_code": return .errorInvalidCode
        case "not_the_child": return .errorNotTheChild
        default: return status >= 500 ? .errorServer : .errorGeneric
        }
    }
}

/// Which screen a signed-in account lands on. A child is recognized here so
/// the parent build does not offer "create a family" to a child account.
public struct ChildDestination: Equatable, Sendable {
    public var memberId: String
    public var familyId: String
    public var familyName: String
    public var status: String
    public var displayName: String
}

public enum RootDestination: Equatable, Sendable {
    case needsFamily
    case parent(familyId: String, familyName: String)
    case child(ChildDestination)
    case membershipPending
}

public enum SessionRoute {
    public static func destination(for me: Me) -> RootDestination {
        if me.memberships.isEmpty { return .needsFamily }
        if let parent = me.memberships.first(where: { $0.role == "parent" && $0.status == "active" }) {
            return .parent(familyId: parent.familyId, familyName: parent.familyName)
        }
        if let child = me.memberships.first(where: { $0.role == "child" }) {
            return .child(ChildDestination(
                memberId: child.memberId,
                familyId: child.familyId,
                familyName: child.familyName,
                status: child.status,
                displayName: child.displayName
            ))
        }
        return .membershipPending
    }
}

public enum PollOutcome: Equatable, Sendable {
    case decided(ParentCase)
    case open(ParentCase)
    case unauthorized
    case failedKeepWaiting
}

public enum CasePolling {
    /// One poll response. A decided colour stops the loop. 401 signs out and
    /// does not look like a network error. Any other failure keeps the last
    /// case and tries again.
    public static func outcome(_ result: Result<ParentCase, APIError>) -> PollOutcome {
        switch result {
        case .success(let item):
            return CaseColor.of(item.color, decidedAt: item.decidedAt).isDecided ? .decided(item) : .open(item)
        case .failure(.http(let status, _)) where status == 401:
            return .unauthorized
        case .failure:
            return .failedKeepWaiting
        }
    }
}
