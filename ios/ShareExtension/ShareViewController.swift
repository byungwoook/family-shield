import FamilyShieldCore
import UIKit
import UniformTypeIdentifiers

/// Accepts a voice note or text from the share sheet, copies it into the App
/// Group, and opens the parent app. Nothing is uploaded here.
final class ShareViewController: UIViewController {
    private let status = UILabel()

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        status.numberOfLines = 0
        status.textAlignment = .center
        status.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(status)
        NSLayoutConstraint.activate([
            status.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 24),
            status.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -24),
            status.centerYAnchor.constraint(equalTo: view.centerYAnchor),
        ])
        status.text = "Family Shield"
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        Task { await ingest() }
    }

    private func ingest() async {
        guard let container = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: AppGroupID.identifier) else {
            status.text = "The App Group is not set up yet. The Apple Developer account needs \(AppGroupID.identifier)."
            return
        }
        let directory = container.appendingPathComponent("share-drafts", isDirectory: true)
        let items = (extensionContext?.inputItems as? [NSExtensionItem]) ?? []
        var text = ""
        var provider: NSItemProvider?
        var typeIdentifier: String?
        for item in items {
            for attachment in item.attachments ?? [] {
                if text.isEmpty, attachment.hasItemConformingToTypeIdentifier(UTType.plainText.identifier) {
                    if let loaded = await Self.load(attachment, type: UTType.plainText.identifier) as? String {
                        text = loaded
                    }
                }
                if provider == nil, let match = Self.audioType(on: attachment) {
                    provider = attachment
                    typeIdentifier = match
                }
            }
        }
        var bytes: Data?
        var displayName: String?
        var declared: Int64?
        if let provider, let typeIdentifier {
            let loaded = await Self.loadAudio(provider, type: typeIdentifier, directory: directory)
            bytes = loaded.bytes
            displayName = loaded.name
            declared = loaded.declared
        }
        let request = ShareRequest(
            action: shareSendAction,
            mime: provider == nil ? (text.isEmpty ? nil : "text/plain") : Self.mime(for: displayName, typeIdentifier: typeIdentifier),
            text: text,
            hasStream: provider != nil,
            displayName: displayName,
            declaredSize: declared
        )
        let outcome = ShareDrafts.receive(request: request, bytes: bytes, draftsDirectory: directory)
        try? ShareDrafts.writeMarker(outcome, directory: directory)
        openHost()
        extensionContext?.completeRequest(returningItems: nil)
    }

    private func openHost() {
        guard let url = URL(string: "\(AppGroupID.urlScheme)://\(AppGroupID.shareHost)") else { return }
        extensionContext?.open(url, completionHandler: { [weak self] accepted in
            if !accepted { self?.openViaResponder(url) }
        })
    }

    private func openViaResponder(_ url: URL) {
        var responder: UIResponder? = self
        let selector = sel_registerName("openURL:")
        while let current = responder {
            if current.responds(to: selector) {
                _ = current.perform(selector, with: url)
                return
            }
            responder = current.next
        }
    }

    private static func audioType(on provider: NSItemProvider) -> String? {
        let candidates = [
            UTType.audio.identifier,
            UTType.mpeg4Audio.identifier,
            "org.xiph.ogg",
            "public.ogg",
        ]
        return candidates.first { provider.hasItemConformingToTypeIdentifier($0) }
    }

    private struct LoadedAudio {
        var bytes: Data?
        var name: String?
        var declared: Int64?
    }

    /// Copies a file URL before the provider invalidates it. A file over 10 MB
    /// is not read into memory.
    private static func loadAudio(_ provider: NSItemProvider, type: String, directory: URL) async -> LoadedAudio {
        await withCheckedContinuation { continuation in
            provider.loadItem(forTypeIdentifier: type, options: nil) { item, _ in
                if let url = item as? URL {
                    let accessed = url.startAccessingSecurityScopedResource()
                    defer { if accessed { url.stopAccessingSecurityScopedResource() } }
                    let name = url.lastPathComponent
                    let size = (try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize).map(Int64.init)
                    if let size, size > VoiceNotes.maxBytes {
                        continuation.resume(returning: LoadedAudio(bytes: nil, name: name, declared: size))
                        return
                    }
                    if size == 0 {
                        continuation.resume(returning: LoadedAudio(bytes: Data(), name: name, declared: 0))
                        return
                    }
                    let temp = directory.appendingPathComponent("incoming-\(UUID().uuidString)")
                    switch VoiceNotes.copyCapped(from: url, to: temp) {
                    case .ok:
                        let data = try? Data(contentsOf: temp)
                        try? FileManager.default.removeItem(at: temp)
                        continuation.resume(returning: LoadedAudio(bytes: data, name: name, declared: size ?? Int64(data?.count ?? 0)))
                    case .tooLarge:
                        continuation.resume(returning: LoadedAudio(bytes: nil, name: name, declared: VoiceNotes.maxBytes + 1))
                    case .empty:
                        continuation.resume(returning: LoadedAudio(bytes: Data(), name: name, declared: 0))
                    case .unreadable:
                        continuation.resume(returning: LoadedAudio(bytes: nil, name: name, declared: nil))
                    }
                    return
                }
                if let data = item as? Data {
                    continuation.resume(returning: LoadedAudio(bytes: data, name: nil, declared: Int64(data.count)))
                    return
                }
                continuation.resume(returning: LoadedAudio(bytes: nil, name: nil, declared: nil))
            }
        }
    }

    private static func load(_ provider: NSItemProvider, type: String) async -> NSSecureCoding? {
        await withCheckedContinuation { continuation in
            provider.loadItem(forTypeIdentifier: type, options: nil) { item, _ in
                continuation.resume(returning: item)
            }
        }
    }

    private static func mime(for fileName: String?, typeIdentifier: String?) -> String {
        if typeIdentifier == "org.xiph.ogg" || typeIdentifier == "public.ogg" {
            return "application/ogg"
        }
        return VoiceNotes.contentType(rawMime: nil, fileName: fileName) ?? "audio/mp4"
    }
}
