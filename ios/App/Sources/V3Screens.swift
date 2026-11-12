import FamilyShieldCore
import SwiftUI
import UIKit

enum FsPalette {
    static func bg(_ scheme: ColorScheme) -> Color {
        scheme == .dark
            ? Color(red: 16 / 255, green: 20 / 255, blue: 25 / 255)
            : Color(red: 243 / 255, green: 240 / 255, blue: 233 / 255)
    }
    static func surface(_ scheme: ColorScheme) -> Color {
        scheme == .dark
            ? Color(red: 29 / 255, green: 35 / 255, blue: 41 / 255)
            : Color(red: 255 / 255, green: 253 / 255, blue: 248 / 255)
    }
    static func text(_ scheme: ColorScheme) -> Color {
        scheme == .dark ? Color(red: 243 / 255, green: 240 / 255, blue: 233 / 255) : Theme.ink
    }
    static func muted(_ scheme: ColorScheme) -> Color {
        scheme == .dark
            ? Color(red: 175 / 255, green: 181 / 255, blue: 174 / 255)
            : Color(red: 103 / 255, green: 107 / 255, blue: 101 / 255)
    }
    static func line(_ scheme: ColorScheme) -> Color {
        scheme == .dark
            ? Color(red: 59 / 255, green: 65 / 255, blue: 71 / 255)
            : Color(red: 213 / 255, green: 212 / 255, blue: 203 / 255)
    }
    static func avatar(_ scheme: ColorScheme) -> Color {
        scheme == .dark
            ? Color(red: 52 / 255, green: 60 / 255, blue: 67 / 255)
            : Color(red: 228 / 255, green: 225 / 255, blue: 216 / 255)
    }
    static func hero(_ scheme: ColorScheme) -> Color {
        scheme == .dark
            ? Color(red: 37 / 255, green: 44 / 255, blue: 51 / 255)
            : Theme.ink
    }
    static let heroMuted = Color(red: 177 / 255, green: 181 / 255, blue: 176 / 255)
    static let heroFuture = Color(red: 152 / 255, green: 161 / 255, blue: 150 / 255)
    static let answerNo = Color(red: 1, green: 153 / 255, blue: 145 / 255)
    static func sheet(_ scheme: ColorScheme) -> Color {
        scheme == .dark
            ? Color(red: 32 / 255, green: 39 / 255, blue: 45 / 255)
            : Color(red: 243 / 255, green: 240 / 255, blue: 233 / 255)
    }
    static func green(_ scheme: ColorScheme) -> Color {
        scheme == .dark
            ? Color(red: 173 / 255, green: 227 / 255, blue: 186 / 255)
            : Color(red: 33 / 255, green: 107 / 255, blue: 64 / 255)
    }
    static func red(_ scheme: ColorScheme) -> Color {
        scheme == .dark ? answerNo : Color(red: 184 / 255, green: 50 / 255, blue: 50 / 255)
    }
    static func yellow(_ scheme: ColorScheme) -> Color {
        scheme == .dark
            ? Color(red: 231 / 255, green: 209 / 255, blue: 124 / 255)
            : Color(red: 128 / 255, green: 97 / 255, blue: 0)
    }
}

struct InitialAvatar: View {
    var name: String
    var size: CGFloat = 56
    var background: Color
    var foreground: Color
    var body: some View {
        Text(V3Format.initial(name))
            .font(Theme.font(size * 0.34, weight: .semibold))
            .foregroundStyle(foreground)
            .frame(width: size, height: size)
            .background(background, in: Circle())
    }
}

struct Waveform: View {
    var color: Color
    var body: some View {
        HStack(alignment: .center, spacing: 3) {
            ForEach(0..<36, id: \.self) { index in
                let peak = 0.25 + 0.75 * Double((index * 17) % 11) / 10
                Capsule()
                    .fill(color)
                    .frame(width: 3, height: 8 + peak * 28)
            }
        }
        .frame(maxWidth: .infinity, minHeight: 36)
    }
}

struct CountdownBar: View {
    var remaining: Int
    @Environment(\.colorScheme) private var scheme
    var body: some View {
        let count = V3Format.segmentCount()
        let current = V3Format.currentSegment(remainingSeconds: remaining)
        HStack(spacing: 3) {
            ForEach(0..<count, id: \.self) { index in
                let color: Color = {
                    if current < 0 { return FsPalette.line(scheme) }
                    if index < current { return FsPalette.text(scheme) }
                    if index == current { return Theme.accent }
                    return FsPalette.line(scheme)
                }()
                RoundedRectangle(cornerRadius: 2).fill(color).frame(height: 10)
            }
        }
    }
}

struct V3ParentHome: View {
    @Bindable var model: FamilyModel
    var onOpen: (String) -> Void
    var onSignOut: () -> Void
    var onChild: (ChildAction, ChildCardState) -> Void
    @Environment(\.colorScheme) private var scheme
    @State private var tab = 0
    @State private var openChildId: String?
    private var locale: AppLocale { AppLocale.resolve() }

    var body: some View {
        VStack(spacing: 0) {
            Group {
                switch tab {
                case 1: history
                case 2: family
                default: home
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            if tab == 2 && openChildId == nil {
                Button(CopyCatalog.text(.familyAddChild, locale)) {
                    model.addName = ""
                    model.addPhone = ""
                    model.addByPhone = false
                    model.showAdd = true
                }
                    .buttonStyle(.borderedProminent)
                    .tint(Theme.accent)
                    .foregroundStyle(Theme.ink)
                    .controlSize(.large)
                    .frame(maxWidth: .infinity)
                    .padding(.horizontal, 20)
                    .padding(.vertical, 8)
                    .accessibilityIdentifier("add_child")
            }
            tabBar
        }
        .background(FsPalette.bg(scheme))
        .accessibilityIdentifier("family_home")
    }

    private var openCase: CaseSummary? {
        model.recent.first { CaseColor.of($0.color, decidedAt: $0.decidedAt) == .open }
    }

    private var home: some View {
        let open = openCase
        return ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                brand
                Text(open == nil ? greeting : CopyCatalog.text(.homeLiveTitle, locale, open?.childDisplayName ?? ""))
                    .font(Theme.font(26, weight: .bold))
                    .foregroundStyle(FsPalette.text(scheme))
                    .padding(.top, 16)
                    .padding(.bottom, 20)
                if let open {
                    liveHero(open)
                } else {
                    idleHero
                }
                if model.home.isEmpty {
                    Text(CopyCatalog.text(.familyEmptyTitle, locale))
                        .font(Theme.font(17, weight: .semibold))
                        .padding(.top, 24)
                        .accessibilityIdentifier("family_empty")
                    Text(CopyCatalog.text(.familyEmptyBody, locale))
                        .font(Theme.font(15))
                        .foregroundStyle(FsPalette.muted(scheme))
                } else {
                    section(CopyCatalog.text(.familyTitleFallback, locale)) { tab = 2 }
                    people
                }
                section(CopyCatalog.text(.familyRecentHeading, locale)) { tab = 1 }
                if let latest = model.recent.first(where: { CaseColor.of($0.color, decidedAt: $0.decidedAt) != .open }) {
                    caseRow(latest)
                } else {
                    Text(CopyCatalog.text(.familyRecentEmpty, locale))
                        .font(Theme.font(15))
                        .foregroundStyle(FsPalette.muted(scheme))
                }
            }
            .padding(.horizontal, 20)
            .padding(.bottom, 24)
        }
    }

    private var idleHero: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(CopyCatalog.text(.homeHeroKicker, locale))
                .font(.system(size: 12, weight: .medium, design: .monospaced))
                .foregroundStyle(FsPalette.heroMuted)
            Text(CopyCatalog.text(.homeHeroTitle, locale))
                .font(Theme.font(24, weight: .semibold))
                .foregroundStyle(Theme.cream)
            Waveform(color: Theme.accent)
            Button(action: { model.openNewCase(preselect: nil) }) {
                HStack {
                    Text(CopyCatalog.text(.familyVerifyMessage, locale))
                    Spacer()
                    Image(systemName: "arrow.right")
                }
                .font(Theme.font(17, weight: .semibold))
                .foregroundStyle(Theme.ink)
                .padding(.horizontal, 20)
                .frame(maxWidth: .infinity, minHeight: 56)
                .background(Theme.accent, in: RoundedRectangle(cornerRadius: 16))
            }
            .accessibilityIdentifier("verify_message")
        }
        .padding(20)
        .background(FsPalette.hero(scheme), in: RoundedRectangle(cornerRadius: 26))
    }

    private func liveHero(_ item: CaseSummary) -> some View {
        let waiting = item.state == "waiting_push"
        let deadline = Times.parse(item.deadlineAt)
        return VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .center) {
                InitialAvatar(name: item.childDisplayName, size: 48, background: Color(red: 228 / 255, green: 225 / 255, blue: 216 / 255), foreground: Theme.ink)
                VStack(alignment: .leading, spacing: 2) {
                    Text(item.childDisplayName).font(Theme.font(20, weight: .semibold)).foregroundStyle(Theme.cream)
                    if let amount = item.requestAmount, !amount.isEmpty {
                        Text(CopyCatalog.text(.homeAmountLine, locale, amount))
                            .font(Theme.font(14))
                            .foregroundStyle(FsPalette.heroMuted)
                    }
                }
                Spacer()
                if waiting, let deadline {
                    TimelineView(.periodic(from: .now, by: 1)) { context in
                        let seconds = V3Format.remainingSeconds(deadline: deadline, now: context.date) ?? 0
                        VStack(alignment: .trailing, spacing: 0) {
                            Text(CopyCatalog.text(.homeUntilCall, locale)).font(Theme.font(12)).foregroundStyle(FsPalette.heroMuted)
                            Text(V3Format.clock(seconds)).font(Theme.font(44, weight: .semibold)).foregroundStyle(Theme.accent)
                        }
                    }
                }
            }
            stepTrio(item.state)
            Button(CopyCatalog.text(.homeOpenProgress, locale)) { onOpen(item.id) }
                .font(Theme.font(17, weight: .semibold))
                .foregroundStyle(Theme.ink)
                .frame(maxWidth: .infinity, minHeight: 56)
                .background(scheme == .dark ? FsPalette.sheet(scheme) : FsPalette.surface(scheme), in: RoundedRectangle(cornerRadius: 16))
        }
        .padding(20)
        .background(FsPalette.hero(scheme), in: RoundedRectangle(cornerRadius: 26))
    }

    private var history: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                brand
                Text(CopyCatalog.text(.historyTitle, locale))
                    .font(Theme.font(32, weight: .bold))
                    .foregroundStyle(FsPalette.text(scheme))
                let decided = model.recent.filter { CaseColor.of($0.color, decidedAt: $0.decidedAt) != .open }
                if decided.isEmpty {
                    Text(CopyCatalog.text(.historyEmpty, locale)).foregroundStyle(FsPalette.muted(scheme))
                } else {
                    ForEach(decided, id: \.id) { row in caseRow(row) }
                }
            }
            .padding(.horizontal, 20)
            .padding(.bottom, 24)
        }
    }

    private var family: some View {
        Group {
            if let child = model.home.children.first(where: { $0.id == openChildId }) {
                familyDetail(child)
            } else {
                familyList
            }
        }
    }

    private var familyList: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                brand
                Text(model.home.familyName).font(Theme.font(32, weight: .bold)).foregroundStyle(FsPalette.text(scheme))
                HStack(spacing: 12) {
                    InitialAvatar(name: model.parentName.isEmpty ? model.home.familyName : model.parentName, size: 52, background: FsPalette.avatar(scheme), foreground: FsPalette.text(scheme))
                    VStack(alignment: .leading) {
                        Text(model.parentName.isEmpty ? model.home.familyName : model.parentName)
                            .font(Theme.font(20, weight: .semibold))
                        Text(CopyCatalog.text(.familyRoleParent, locale))
                            .font(Theme.font(14))
                            .foregroundStyle(FsPalette.muted(scheme))
                    }
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(FsPalette.surface(scheme), in: RoundedRectangle(cornerRadius: 24))
                HStack {
                    Text(CopyCatalog.text(.familyChildCount, locale, model.home.children.count))
                        .font(Theme.font(20, weight: .semibold))
                    Spacer()
                    Button(CopyCatalog.text(.familyInviteLink, locale)) {
                        model.addName = ""
                        model.addPhone = ""
                        model.addByPhone = false
                        model.showAdd = true
                    }
                    .font(Theme.font(15))
                    .foregroundStyle(FsPalette.muted(scheme))
                }
                if model.home.isEmpty {
                    Text(CopyCatalog.text(.familyEmptyTitle, locale)).accessibilityIdentifier("family_empty")
                } else {
                    VStack(spacing: 0) {
                        ForEach(model.home.children) { child in
                            familyRow(child)
                            if child.id != model.home.children.last?.id {
                                Divider().padding(.leading, 76)
                            }
                        }
                    }
                    .background(FsPalette.surface(scheme), in: RoundedRectangle(cornerRadius: 24))
                }
            }
            .padding(.horizontal, 20)
            .padding(.bottom, 16)
        }
    }

    private func familyRow(_ child: ChildCardState) -> some View {
        let last4 = model.members.first { $0.id == child.id }?.phoneLast4
        return Button { openChildId = child.id } label: {
            HStack(spacing: 12) {
                InitialAvatar(name: child.name, size: 48, background: FsPalette.avatar(scheme), foreground: FsPalette.text(scheme))
                VStack(alignment: .leading, spacing: 2) {
                    Text(child.name).font(Theme.font(17, weight: .semibold)).foregroundStyle(FsPalette.text(scheme))
                    if child.canVerify {
                        Text(CopyCatalog.text(.familyCanCheck, locale)).font(Theme.font(14)).foregroundStyle(FsPalette.muted(scheme))
                    }
                    if let last4, !last4.isEmpty {
                        Text(CopyCatalog.text(.familyNumberEnding, locale, last4)).font(Theme.font(14)).foregroundStyle(FsPalette.muted(scheme))
                    }
                }
                Spacer()
                Image(systemName: "chevron.right").foregroundStyle(FsPalette.muted(scheme))
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 14)
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("child_\(child.id)")
    }

    private func familyDetail(_ child: ChildCardState) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Button { openChildId = nil } label: {
                        Image(systemName: "chevron.left").frame(width: 44, height: 44)
                    }
                    .accessibilityIdentifier("back")
                    Text(child.name).font(Theme.font(17, weight: .semibold)).frame(maxWidth: .infinity)
                    Color.clear.frame(width: 44, height: 44)
                }
                ChildCard(child: child, busy: model.busy) { action in onChild(action, child) }
            }
            .padding(.horizontal, 20)
            .padding(.bottom, 24)
        }
    }

    private var people: some View {
        HStack(alignment: .top, spacing: 18) {
            ForEach(model.members.filter { MemberRules.isChild($0) }.prefix(6), id: \.id) { member in
                VStack(spacing: 6) {
                    InitialAvatar(name: member.displayName, size: 64, background: FsPalette.avatar(scheme), foreground: FsPalette.text(scheme))
                    Text(member.displayName).font(Theme.font(15, weight: .semibold)).lineLimit(1)
                    Text(CopyCatalog.text(.homeUsingApp, locale)).font(Theme.font(12)).foregroundStyle(FsPalette.muted(scheme))
                }
                .frame(width: 72)
            }
            Button {
                model.addName = ""
                model.addPhone = ""
                model.addByPhone = false
                model.showAdd = true
            } label: {
                VStack(spacing: 6) {
                    Image(systemName: "plus")
                        .frame(width: 64, height: 64)
                        .overlay(Circle().stroke(FsPalette.line(scheme), lineWidth: 1))
                    Text(CopyCatalog.text(.familyAddChild, locale)).font(Theme.font(13, weight: .semibold))
                    Text(CopyCatalog.text(.familyInviteLink, locale)).font(Theme.font(12)).foregroundStyle(FsPalette.muted(scheme))
                }
                .frame(width: 72)
            }
            .buttonStyle(.plain)
            .foregroundStyle(FsPalette.text(scheme))
        }
        .padding(.top, 8)
    }

    private func caseRow(_ item: CaseSummary) -> some View {
        let color = CaseColor.of(item.color, decidedAt: item.decidedAt)
        let label: String = switch color {
        case .green: CopyCatalog.text(.historyGreen, locale)
        case .red: CopyCatalog.text(.historyRed, locale)
        case .yellow: CopyCatalog.text(.historyYellow, locale)
        case .open: CopyCatalog.text(.cdStatusOpen, locale)
        }
        let tint: Color = switch color {
        case .green: FsPalette.green(scheme)
        case .red: FsPalette.red(scheme)
        case .yellow: FsPalette.yellow(scheme)
        case .open: FsPalette.text(scheme)
        }
        return Button { onOpen(item.id) } label: {
            HStack(spacing: 12) {
                InitialAvatar(name: item.childDisplayName, size: 44, background: FsPalette.avatar(scheme), foreground: FsPalette.text(scheme))
                VStack(alignment: .leading, spacing: 2) {
                    Text(CopyCatalog.text(.caseTitle, locale, item.childDisplayName))
                        .font(Theme.font(17, weight: .semibold))
                        .foregroundStyle(FsPalette.text(scheme))
                    if let amount = item.requestAmount, !amount.isEmpty {
                        Text(CopyCatalog.text(.homeAmountLine, locale, amount))
                            .font(Theme.font(14))
                            .foregroundStyle(FsPalette.muted(scheme))
                    }
                }
                Spacer()
                Text(label).font(Theme.font(14, weight: .semibold)).foregroundStyle(tint)
            }
            .padding(14)
            .background(FsPalette.surface(scheme), in: RoundedRectangle(cornerRadius: 20))
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("recent_\(item.id)")
    }

    private var brand: some View {
        HStack {
            Text(CopyCatalog.text(.homeBrand, locale))
                .font(.system(size: 12, weight: .medium, design: .monospaced))
                .foregroundStyle(FsPalette.muted(scheme))
            Spacer()
            Menu {
                Button(CopyCatalog.text(.cdRefresh, locale)) { Task { await model.refresh() } }
                    .accessibilityIdentifier("refresh")
                Button(CopyCatalog.text(.actionSignOut, locale), action: onSignOut)
            } label: {
                InitialAvatar(
                    name: model.parentName.isEmpty ? model.home.familyName : model.parentName,
                    size: 40,
                    background: Theme.ink,
                    foreground: FsPalette.bg(scheme)
                )
            }
        }
        .padding(.top, 8)
    }

    private func section(_ title: String, action: @escaping () -> Void) -> some View {
        HStack {
            Text(title).font(Theme.font(20, weight: .bold)).foregroundStyle(FsPalette.text(scheme))
            Spacer()
            Button(CopyCatalog.text(.homeSeeAll, locale), action: action)
                .font(Theme.font(14))
                .foregroundStyle(FsPalette.muted(scheme))
        }
        .padding(.top, 28)
        .padding(.bottom, 12)
    }

    private func stepTrio(_ state: String) -> some View {
        let active = state == "calling" ? 2 : (state == "awaiting_answer" ? 1 : 0)
        let labels = [
            CopyCatalog.text(.homeStepPush, locale),
            CopyCatalog.text(.homeStepBio, locale),
            CopyCatalog.text(.homeStepCall, locale),
        ]
        return HStack {
            ForEach(Array(labels.enumerated()), id: \.offset) { index, label in
                let color = index <= active ? Theme.accent : FsPalette.heroFuture
                VStack(spacing: 4) {
                    Image(systemName: index == 0 ? "iphone" : (index == 1 ? "faceid" : "phone"))
                        .foregroundStyle(color)
                    Text(label).font(Theme.font(12, weight: .medium)).foregroundStyle(color)
                }
                .frame(maxWidth: .infinity)
            }
        }
    }

    private var greeting: String {
        model.parentName.isEmpty
            ? CopyCatalog.text(.homeGreetingPlain, locale)
            : CopyCatalog.text(.homeGreeting, locale, model.parentName)
    }

    private var tabBar: some View {
        HStack {
            tabButton(0, "house", .tabHome)
            tabButton(1, "clock.arrow.circlepath", .tabHistory)
            tabButton(2, "person.2", .tabFamily)
        }
        .padding(.top, 6)
        .frame(height: 64)
        .background(FsPalette.bg(scheme))
        .overlay(alignment: .top) { Rectangle().fill(FsPalette.line(scheme)).frame(height: 0.5) }
    }

    private func tabButton(_ index: Int, _ symbol: String, _ key: CopyKey) -> some View {
        let selected = tab == index
        return Button { tab = index } label: {
            VStack(spacing: 2) {
                Image(systemName: symbol).frame(width: 44, height: 28)
                Text(CopyCatalog.text(key, locale)).font(Theme.font(12, weight: .medium))
            }
            .foregroundStyle(selected ? FsPalette.text(scheme) : FsPalette.muted(scheme))
            .frame(maxWidth: .infinity, minHeight: 44)
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier(index == 0 ? "tab_home" : (index == 1 ? "tab_history" : "tab_family"))
    }
}

struct V3CaseBody: View {
    var item: ParentCase
    var view: CasePresentation
    var onBack: () -> Void
    var onCopy: (String) -> Void
    var onShare: (String) -> Void
    @Environment(\.colorScheme) private var scheme
    @State private var detailsOpen = false
    private var locale: AppLocale { AppLocale.resolve() }

    var body: some View {
        switch view.color {
        case .green, .red:
            result
        case .open:
            progress
        case .yellow:
            yellow
        }
    }

    private var progress: some View {
        let waiting = item.state == "waiting_push"
        let deadline = Times.parse(item.deadlineAt)
        return ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                nav(CopyCatalog.text(.caseTitle, locale, view.name), ink: false)
                HStack(spacing: 12) {
                    InitialAvatar(name: view.name, size: 56, background: FsPalette.avatar(scheme), foreground: FsPalette.text(scheme))
                    VStack(alignment: .leading) {
                        Text(view.name).font(Theme.font(20, weight: .semibold))
                        if let amount = item.claims?.amount.flatMap(known) {
                            Text(CopyCatalog.text(.homeAmountLine, locale, amount)).foregroundStyle(FsPalette.muted(scheme))
                        }
                    }
                }
                if waiting, let deadline {
                    TimelineView(.periodic(from: .now, by: 1)) { context in
                        let seconds = V3Format.remainingSeconds(deadline: deadline, now: context.date) ?? 0
                        VStack(spacing: 8) {
                            Text(CopyCatalog.text(.homeUntilCall, locale)).foregroundStyle(FsPalette.muted(scheme))
                            Text(V3Format.clock(seconds)).font(Theme.font(64, weight: .semibold))
                            CountdownBar(remaining: seconds)
                            Text(CopyCatalog.text(.progressWaiting, locale))
                        }
                        .frame(maxWidth: .infinity)
                    }
                } else if let line = view.openLine {
                    Text(line).font(Theme.font(17))
                }
                if let dont = view.dontSend {
                    Text(dont)
                        .font(Theme.font(17, weight: .semibold))
                        .frame(maxWidth: .infinity)
                        .accessibilityIdentifier("dont_send")
                }
                if let text = view.parentText, !text.isEmpty {
                    Text(CopyCatalog.text(.progressVoiceLabel, locale)).font(Theme.font(16, weight: .semibold))
                    Text(CopyCatalog.text(.progressTextOnly, locale)).font(Theme.font(14)).foregroundStyle(FsPalette.muted(scheme))
                    Text(text).font(Theme.font(15))
                }
            }
            .padding(20)
        }
        .background(FsPalette.bg(scheme))
        .accessibilityIdentifier("case_screen")
    }

    private var result: some View {
        let confirmed = view.color == .green
        let subject = V3Format.subject(view.name, korean: locale == .ko)
        let headline = CopyCatalog.text(confirmed ? .v3HeadlineYes : .v3HeadlineNo, locale, subject)
        let bubble = confirmed ? Theme.accent : FsPalette.answerNo
        return VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    nav(CopyCatalog.text(.v3ResultNav, locale), ink: true)
                    Text(CopyCatalog.text(.v3Direct, locale))
                        .font(.system(size: 12, weight: .medium, design: .monospaced))
                        .foregroundStyle(FsPalette.heroMuted)
                    HStack(alignment: .center, spacing: 0) {
                        VStack(spacing: 6) {
                            InitialAvatar(name: view.name, size: 72, background: Color(red: 228 / 255, green: 225 / 255, blue: 216 / 255), foreground: Theme.ink)
                            Text(view.name).font(Theme.font(14)).foregroundStyle(Theme.cream)
                        }
                        .frame(width: 72)
                        .padding(.leading, 15)
                        VStack(alignment: .leading, spacing: 2) {
                            HStack(spacing: 6) {
                                ScanFaceMark()
                                Text(CopyCatalog.text(.v3AnswerCaption, locale))
                                    .font(Theme.font(12, weight: .medium))
                                    .foregroundStyle(Theme.ink)
                            }
                            Text(CopyCatalog.text(confirmed ? .childYes : .childNo, locale))
                                .font(Theme.font(38, weight: .bold))
                                .foregroundStyle(Theme.ink)
                            Text(CopyCatalog.text(confirmed ? .v3YesDetail : .v3NoDetail, locale))
                                .font(Theme.font(14))
                                .foregroundStyle(Theme.ink)
                        }
                        .frame(maxWidth: .infinity, minHeight: 128, alignment: .leading)
                        .padding(.leading, 30)
                        .padding(.trailing, 20)
                        .padding(.vertical, 16)
                        .background(bubble, in: AnswerBubble())
                        .padding(.leading, 16)
                        .padding(.trailing, 15)
                    }
                    Text(headline)
                        .font(Theme.font(38, weight: .bold))
                        .tracking(-1)
                        .foregroundStyle(Theme.cream)
                        .padding(.top, 12)
                    HStack {
                        if let amount = resultAmount {
                            Text(CopyCatalog.text(.homeAmountLine, locale, amount))
                                .font(Theme.font(14))
                                .foregroundStyle(FsPalette.heroMuted)
                        }
                        Spacer(minLength: 8)
                        if !resultWhen.isEmpty {
                            Text(resultWhen)
                                .font(Theme.font(14))
                                .foregroundStyle(FsPalette.heroMuted)
                        }
                    }
                }
                .padding(20)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
            sheet(confirmed: confirmed)
        }
        .background(Theme.ink)
        .accessibilityIdentifier("case_screen")
    }

    private func sheet(confirmed: Bool) -> some View {
        let shortLine = confirmed
            ? CopyCatalog.text(.v3SheetYesBody, locale, view.name)
            : CopyCatalog.text(.v3SheetScamLine, locale)
        return VStack(alignment: .leading, spacing: 8) {
            Text(CopyCatalog.text(confirmed ? .v3SheetYes : .v3SheetScam, locale))
                .font(Theme.font(20, weight: .bold))
                .foregroundStyle(FsPalette.text(scheme))
                .accessibilityIdentifier("result_title")
            keptText(shortLine, size: 15, color: FsPalette.muted(scheme))
            Button(CopyCatalog.text(detailsOpen ? .v3DetailsHide : .v3Details, locale)) {
                detailsOpen.toggle()
            }
            .font(Theme.font(15, weight: .medium))
            .foregroundStyle(FsPalette.text(scheme))
            .frame(minHeight: 44, alignment: .leading)
            .accessibilityIdentifier("result_details")
            if detailsOpen {
                ScrollView {
                    VStack(alignment: .leading, spacing: 8) {
                        if !view.body.isEmpty {
                            keptText(view.body, size: 15, color: FsPalette.muted(scheme)).accessibilityIdentifier("result_body")
                        }
                        if !confirmed {
                            if let alert = view.familyAlert {
                                Text(CopyCatalog.text(.familyAlertHeading, locale)).font(Theme.font(16, weight: .semibold))
                                Text(alert).font(Theme.font(15)).accessibilityIdentifier("family_alert")
                                Button(CopyCatalog.text(.actionCopy, locale)) { onCopy(alert) }
                                    .accessibilityIdentifier("alert_copy")
                            }
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .frame(maxHeight: 240)
            }
            if confirmed {
                Button(CopyCatalog.text(.v3Done, locale), action: onBack)
                    .buttonStyle(.borderedProminent)
                    .tint(Theme.accent)
                    .foregroundStyle(Theme.ink)
                    .frame(maxWidth: .infinity)
            } else if view.familyAlert != nil {
                Button { if let alert = view.familyAlert { onShare(alert) } } label: {
                    Text(CopyCatalog.text(.v3Share, locale))
                        .font(Theme.font(17, weight: .semibold))
                        .foregroundStyle(Theme.ink)
                        .frame(maxWidth: .infinity, minHeight: 56)
                        .background(FsPalette.answerNo, in: RoundedRectangle(cornerRadius: 16))
                }
                .buttonStyle(.plain)
            }
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(FsPalette.sheet(scheme), in: RoundedRectangle(cornerRadius: 24))
        .padding(.horizontal, 20)
        .padding(.bottom, 20)
        .accessibilityIdentifier("result_card")
    }

    private var yellow: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                nav(CopyCatalog.text(.cdStatusYellow, locale), ink: false)
                Text(view.title).font(Theme.font(32, weight: .bold)).foregroundStyle(FsPalette.yellow(scheme)).accessibilityIdentifier("result_title")
                Text(view.body).font(Theme.font(17)).accessibilityIdentifier("result_body")
                if let dont = view.dontSend { Text(dont).accessibilityIdentifier("dont_send") }
            }
            .padding(20)
        }
        .background(FsPalette.bg(scheme))
        .accessibilityIdentifier("case_screen")
    }

    private func nav(_ title: String, ink: Bool) -> some View {
        HStack {
            Button(action: onBack) {
                Image(systemName: "chevron.left")
                    .frame(width: 44, height: 44)
            }
            .accessibilityIdentifier("back")
            .foregroundStyle(ink ? Theme.cream : FsPalette.text(scheme))
            Text(title)
                .font(Theme.font(17, weight: .semibold))
                .frame(maxWidth: .infinity)
                .foregroundStyle(ink ? Theme.cream : FsPalette.text(scheme))
            Color.clear.frame(width: 44, height: 44)
        }
    }

    private func known(_ value: String?) -> String? {
        guard let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines), !trimmed.isEmpty else { return nil }
        if trimmed.caseInsensitiveCompare("unknown") == .orderedSame { return nil }
        return trimmed
    }

    private var resultAmount: String? { known(item.claims?.amount) }

    private var resultWhen: String {
        let time = Times.shortTime(item.decidedAt, locale: .current)
        guard !time.isEmpty, let date = Times.parse(item.decidedAt) else { return "" }
        if Calendar.current.isDateInToday(date) {
            return CopyCatalog.text(.v3Today, locale) + " " + time
        }
        if Calendar.current.isDateInYesterday(date) {
            return CopyCatalog.text(.v3Yesterday, locale) + " " + time
        }
        return time
    }
}

private func keptText(_ string: String, size: CGFloat, weight: Font.Weight = .regular, color: Color) -> Text {
    let style = NSMutableParagraphStyle()
    style.lineBreakStrategy = .hangulWordPriority
    var container = AttributeContainer()
    container.font = Font.custom("Pretendard Variable", size: size).weight(weight)
    container.foregroundColor = color
    container.paragraphStyle = style
    return Text(AttributedString(string, attributes: container))
}

private struct AnswerBubble: Shape {
    func path(in rect: CGRect) -> Path {
        let tail: CGFloat = 10
        let radius: CGFloat = 22
        var path = Path()
        let body = CGRect(x: rect.minX + tail, y: rect.minY, width: max(0, rect.width - tail), height: rect.height)
        path.addRoundedRect(in: body, cornerSize: CGSize(width: radius, height: radius))
        let midY = rect.midY
        path.move(to: CGPoint(x: body.minX, y: midY - tail * 0.9))
        path.addLine(to: CGPoint(x: rect.minX, y: midY))
        path.addLine(to: CGPoint(x: body.minX, y: midY + tail * 0.75))
        path.closeSubpath()
        return path
    }
}

private struct ScanFaceMark: View {
    var body: some View {
        Canvas { context, size in
            let ink = GraphicsContext.Shading.color(Theme.ink)
            let stroke = StrokeStyle(lineWidth: 1.5, lineCap: .round, lineJoin: .round)
            func line(_ start: CGPoint, _ end: CGPoint) {
                var path = Path()
                path.move(to: start)
                path.addLine(to: end)
                context.stroke(path, with: ink, style: stroke)
            }
            let width = size.width
            let inset = width * 0.16
            let turn = width * 0.42
            let far = width - inset
            let back = width - turn
            line(CGPoint(x: inset, y: turn), CGPoint(x: inset, y: inset))
            line(CGPoint(x: inset, y: inset), CGPoint(x: turn, y: inset))
            line(CGPoint(x: far, y: turn), CGPoint(x: far, y: inset))
            line(CGPoint(x: far, y: inset), CGPoint(x: back, y: inset))
            line(CGPoint(x: inset, y: back), CGPoint(x: inset, y: far))
            line(CGPoint(x: inset, y: far), CGPoint(x: turn, y: far))
            line(CGPoint(x: far, y: back), CGPoint(x: far, y: far))
            line(CGPoint(x: far, y: far), CGPoint(x: back, y: far))
            context.fill(Path(ellipseIn: CGRect(x: width * 0.35, y: width * 0.40, width: width * 0.08, height: width * 0.08)), with: ink)
            context.fill(Path(ellipseIn: CGRect(x: width * 0.57, y: width * 0.40, width: width * 0.08, height: width * 0.08)), with: ink)
            var smile = Path()
            smile.addArc(
                center: CGPoint(x: width * 0.5, y: width * 0.55),
                radius: width * 0.16,
                startAngle: .degrees(20),
                endAngle: .degrees(160),
                clockwise: false
            )
            context.stroke(smile, with: ink, style: stroke)
        }
        .frame(width: 16, height: 16)
        .accessibilityHidden(true)
    }
}
