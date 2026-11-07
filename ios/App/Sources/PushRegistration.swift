import UIKit
import UserNotifications

/// Registers an APNs device token. Debug posts `env=sandbox` (the development
/// entitlement). Release posts `env=production`. A missing token is a no-op:
/// this tree has no APNs key, and the simulator often has no token.
final class PushAppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        Task { @MainActor in
            AppRuntime.shared.notePushToken(token)
        }
    }

    func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error) {
        // No token, no log. The fallback call still works.
    }
}

@MainActor
enum PushRegistration {
    static func requestAndRegister() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, _ in
            guard granted else { return }
            DispatchQueue.main.async {
                UIApplication.shared.registerForRemoteNotifications()
            }
        }
    }
}
