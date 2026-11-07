import Foundation
import Security

/// Session token in the Keychain. The preferences file never holds it.
/// `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly` keeps it off iCloud and
/// off other devices.
final class KeychainTokenStore: TokenProviding, @unchecked Sendable {
    private let lock = NSLock()
    private var cached: String?
    private let service = "com.familyshield.app.session"
    private let account = "session"

    func load() {
        lock.lock()
        cached = read()
        lock.unlock()
    }

    func currentToken() -> String? {
        lock.lock()
        defer { lock.unlock() }
        return cached
    }

    func save(_ token: String) {
        let data = Data(token.utf8)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        SecItemDelete(query as CFDictionary)
        var add = query
        add[kSecValueData as String] = data
        add[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        SecItemAdd(add as CFDictionary, nil)
        lock.lock()
        cached = token
        lock.unlock()
    }

    func clear() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        SecItemDelete(query as CFDictionary)
        lock.lock()
        cached = nil
        lock.unlock()
    }

    private func read() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data,
              let token = String(data: data, encoding: .utf8),
              !token.isEmpty
        else { return nil }
        return token
    }
}

enum APIBase {
    /// `FS_API_BASE` in the process environment wins, then Info.plist `FSApiBase`.
    /// Release ships an empty plist value, so a store build does not call localhost.
    static var current: String {
        let env = ProcessInfo.processInfo.environment["FS_API_BASE"]?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if !env.isEmpty { return env }
        let plist = Bundle.main.object(forInfoDictionaryKey: "FSApiBase") as? String ?? ""
        return plist.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

/// Lets the API client's 401 callback reach the model after `init` returns.
final class SignOutHook: @unchecked Sendable {
    var fire: @Sendable (String) -> Void = { _ in }
}
