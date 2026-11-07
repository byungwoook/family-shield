import CallKit
import Foundation
import FamilyShieldCore

/// Identifies one number, the configured outbound caller id, as "Family Shield".
/// The extension adds no blocking entries and reads no call audio.
final class CallDirectoryHandler: CXCallDirectoryProvider {
    override func beginRequest(with context: CXCallDirectoryExtensionContext) {
        context.delegate = self
        let raw = Bundle.main.object(forInfoDictionaryKey: "FSOutboundCallerId") as? String ?? ""
        let configured = raw.isEmpty || raw.contains("$(") ? OutboundIdentification.placeholderE164 : raw
        // The first load is a full reload and replaces the directory with this one entry.
        // Later reloads are incremental. The set does not change until the next build,
        // so an incremental pass leaves the entry that the full reload already wrote.
        if !context.isIncremental {
            for entry in OutboundIdentification.entries(configured: configured) {
                context.addIdentificationEntry(
                    withNextSequentialPhoneNumber: entry.phoneNumber,
                    label: entry.label
                )
            }
        }
        context.completeRequest()
    }
}

extension CallDirectoryHandler: CXCallDirectoryExtensionContextDelegate {
    func requestFailed(for extensionContext: CXCallDirectoryExtensionContext, withError error: Error) {
        // Optional. A failed reload leaves the phone unlabeled. The check code still works.
    }
}
