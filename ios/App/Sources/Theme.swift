import FamilyShieldCore
import SwiftUI

enum Theme {
    static let accent = Color(red: 0.12, green: 0.29, blue: 0.43)

    static func background(_ color: CaseColor, scheme: ColorScheme) -> Color {
        switch (color, scheme) {
        case (.green, .dark): return Color(red: 0.08, green: 0.22, blue: 0.14)
        case (.green, _): return Color(red: 0.90, green: 0.96, blue: 0.92)
        case (.red, .dark): return Color(red: 0.28, green: 0.10, blue: 0.10)
        case (.red, _): return Color(red: 0.99, green: 0.93, blue: 0.93)
        case (.yellow, .dark): return Color(red: 0.28, green: 0.22, blue: 0.08)
        case (.yellow, _): return Color(red: 1.0, green: 0.96, blue: 0.84)
        case (.open, .dark): return Color(red: 0.12, green: 0.16, blue: 0.22)
        case (.open, _): return Color(red: 0.93, green: 0.95, blue: 0.97)
        }
    }

    static func foreground(_ color: CaseColor, scheme: ColorScheme) -> Color {
        switch (color, scheme) {
        case (.green, .dark): return Color(red: 0.72, green: 0.90, blue: 0.78)
        case (.green, _): return Color(red: 0.04, green: 0.37, blue: 0.20)
        case (.red, .dark): return Color(red: 0.98, green: 0.78, blue: 0.76)
        case (.red, _): return Color(red: 0.61, green: 0.11, blue: 0.11)
        case (.yellow, .dark): return Color(red: 1.0, green: 0.90, blue: 0.62)
        case (.yellow, _): return Color(red: 0.42, green: 0.31, blue: 0.0)
        case (.open, .dark): return Color(red: 0.86, green: 0.90, blue: 0.94)
        case (.open, _): return Color(red: 0.10, green: 0.18, blue: 0.28)
        }
    }
}

struct Banner: View {
    var text: String
    var tone: Color = .red
    var body: some View {
        Text(text)
            .font(.body)
            .foregroundStyle(tone)
            .frame(maxWidth: .infinity, alignment: .leading)
            .accessibilityIdentifier("banner")
    }
}

struct PrimaryButton: View {
    var title: String
    var identifier: String
    var enabled: Bool = true
    var action: () -> Void
    var body: some View {
        Button(title, action: action)
            .buttonStyle(.borderedProminent)
            .tint(Theme.accent)
            .controlSize(.large)
            .frame(maxWidth: .infinity)
            .disabled(!enabled)
            .accessibilityIdentifier(identifier)
    }
}
