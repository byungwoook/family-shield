import CallKit
import FamilyShieldCore
import Foundation

/// Opens the system Call Blocking & Identification setting and reloads our extension.
/// Enabling it is optional. The check code works without it.
enum CallDirectoryLink {
    static let extensionIdentifier = OutboundIdentification.extensionBundleId

    static func openSettings() {
        CXCallDirectoryManager.sharedInstance.openSettings { _ in }
    }

    static func reload() {
        CXCallDirectoryManager.sharedInstance.reloadExtension(withIdentifier: extensionIdentifier) { _ in }
    }

    static func refresh(_ done: @escaping (Bool) -> Void) {
        CXCallDirectoryManager.sharedInstance.getEnabledStatusForExtension(withIdentifier: extensionIdentifier) { status, _ in
            DispatchQueue.main.async {
                done(status == .enabled)
            }
        }
    }
}
