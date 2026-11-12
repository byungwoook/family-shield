import Foundation

// Wire types for docs/API_CONTRACT.md. Request bodies are built by APIClient
// and contain only documented fields. Unknown response fields are ignored.
// State, result, color, role, and status stay strings so a new server value
// still parses; domain helpers decide what the screen does with them.

public struct NonceResponse: Codable, Equatable, Sendable {
    public var nonce: String
    public var expiresAt: String
}

public struct SessionResponse: Codable, Equatable, Sendable {
    public var token: String
    public var userId: String
}

public struct DevLoginResponse: Codable, Equatable, Sendable {
    public var token: String
    public var userId: String
    public var authSubject: String
}

public struct Me: Codable, Equatable, Sendable {
    public var userId: String
    public var displayName: String
    public var locale: String
    public var memberships: [Membership]

    public init(userId: String, displayName: String = "", locale: String = "en", memberships: [Membership] = []) {
        self.userId = userId
        self.displayName = displayName
        self.locale = locale
        self.memberships = memberships
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        userId = try c.decode(String.self, forKey: .userId)
        displayName = try c.decodeIfPresent(String.self, forKey: .displayName) ?? ""
        locale = try c.decodeIfPresent(String.self, forKey: .locale) ?? "en"
        memberships = try c.decodeIfPresent([Membership].self, forKey: .memberships) ?? []
    }
}

public struct Membership: Codable, Equatable, Sendable {
    public var memberId: String
    public var familyId: String
    public var familyName: String
    public var role: String
    public var status: String
    public var displayName: String

    public init(memberId: String, familyId: String, familyName: String = "", role: String, status: String, displayName: String = "") {
        self.memberId = memberId
        self.familyId = familyId
        self.familyName = familyName
        self.role = role
        self.status = status
        self.displayName = displayName
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        memberId = try c.decode(String.self, forKey: .memberId)
        familyId = try c.decode(String.self, forKey: .familyId)
        familyName = try c.decodeIfPresent(String.self, forKey: .familyName) ?? ""
        role = try c.decode(String.self, forKey: .role)
        status = try c.decode(String.self, forKey: .status)
        displayName = try c.decodeIfPresent(String.self, forKey: .displayName) ?? ""
    }
}

public struct FamilyCreated: Codable, Equatable, Sendable {
    public var id: String
    public var name: String
    public init(id: String, name: String) {
        self.id = id
        self.name = name
    }
}

public struct ChildInvite: Codable, Equatable, Sendable {
    public var id: String
    public var displayName: String
    public var status: String
    public var inviteSecret: String
    public var inviteExpiresAt: String
}

public struct InviteReissued: Codable, Equatable, Sendable {
    public var id: String
    public var inviteSecret: String
    public var inviteExpiresAt: String
}

public struct Roster: Codable, Equatable, Sendable {
    public var familyId: String
    public var members: [Member]

    public init(familyId: String, members: [Member] = []) {
        self.familyId = familyId
        self.members = members
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        familyId = try c.decode(String.self, forKey: .familyId)
        members = try c.decodeIfPresent([Member].self, forKey: .members) ?? []
    }
}

public struct Member: Codable, Equatable, Sendable {
    public var id: String
    public var role: String
    public var displayName: String
    public var status: String
    public var linked: Bool
    public var phoneLast4: String?
    public var pendingPhoneLast4: String?
    public var phoneVerified: Bool
    public var hasCheckCode: Bool
    public var awaitingConfirm: Bool
    public var inviteExpiresAt: String?
    public var callOnly: Bool
    public var allowLinkOpen: Bool
    public var confirmedAt: String?

    public init(
        id: String,
        role: String,
        displayName: String = "",
        status: String,
        linked: Bool = false,
        phoneLast4: String? = nil,
        pendingPhoneLast4: String? = nil,
        phoneVerified: Bool = false,
        hasCheckCode: Bool = false,
        awaitingConfirm: Bool = false,
        inviteExpiresAt: String? = nil,
        callOnly: Bool = false,
        allowLinkOpen: Bool = false,
        confirmedAt: String? = nil
    ) {
        self.id = id
        self.role = role
        self.displayName = displayName
        self.status = status
        self.linked = linked
        self.phoneLast4 = phoneLast4
        self.pendingPhoneLast4 = pendingPhoneLast4
        self.phoneVerified = phoneVerified
        self.hasCheckCode = hasCheckCode
        self.awaitingConfirm = awaitingConfirm
        self.inviteExpiresAt = inviteExpiresAt
        self.callOnly = callOnly
        self.allowLinkOpen = allowLinkOpen
        self.confirmedAt = confirmedAt
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        role = try c.decode(String.self, forKey: .role)
        displayName = try c.decodeIfPresent(String.self, forKey: .displayName) ?? ""
        status = try c.decode(String.self, forKey: .status)
        linked = try c.decodeIfPresent(Bool.self, forKey: .linked) ?? false
        phoneLast4 = try c.decodeIfPresent(String.self, forKey: .phoneLast4)
        pendingPhoneLast4 = try c.decodeIfPresent(String.self, forKey: .pendingPhoneLast4)
        phoneVerified = try c.decodeIfPresent(Bool.self, forKey: .phoneVerified) ?? false
        hasCheckCode = try c.decodeIfPresent(Bool.self, forKey: .hasCheckCode) ?? false
        awaitingConfirm = try c.decodeIfPresent(Bool.self, forKey: .awaitingConfirm) ?? false
        inviteExpiresAt = try c.decodeIfPresent(String.self, forKey: .inviteExpiresAt)
        callOnly = try c.decodeIfPresent(Bool.self, forKey: .callOnly) ?? false
        allowLinkOpen = try c.decodeIfPresent(Bool.self, forKey: .allowLinkOpen) ?? false
        confirmedAt = try c.decodeIfPresent(String.self, forKey: .confirmedAt)
    }
}

public enum ParentDecision: String, Sendable {
    case confirm
    case reject
}

public struct MemberDecision: Codable, Equatable, Sendable {
    public var id: String
    public var status: String
    public var phoneLast4: String?
}

public struct PhoneChangeDecision: Codable, Equatable, Sendable {
    public var id: String
    public var status: String
    public var phoneLast4: String?
    public var cancelledCases: Int?
}

public struct LinkSent: Codable, Equatable, Sendable {
    public var status: String
    public var phoneLast4: String?
}

public struct Claims: Codable, Equatable, Sendable {
    public var claimedIdentity: String?
    public var amount: String?
    public var story: String?
    public var redFlags: [String]

    public init(claimedIdentity: String? = nil, amount: String? = nil, story: String? = nil, redFlags: [String] = []) {
        self.claimedIdentity = claimedIdentity
        self.amount = amount
        self.story = story
        self.redFlags = redFlags
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        claimedIdentity = try c.decodeIfPresent(String.self, forKey: .claimedIdentity)
        amount = try c.decodeIfPresent(String.self, forKey: .amount)
        story = try c.decodeIfPresent(String.self, forKey: .story)
        redFlags = try c.decodeIfPresent([String].self, forKey: .redFlags) ?? []
    }
}

public struct ParentCase: Codable, Equatable, Sendable {
    public var id: String
    public var familyId: String
    public var childMemberId: String
    public var childDisplayName: String
    public var state: String
    public var result: String?
    public var color: String
    public var answeredVia: String?
    public var codeChannel: String?
    public var gather: String?
    public var parentText: String
    public var transcript: String?
    public var claims: Claims?
    public var patternId: String?
    public var timeline: [String]
    public var phoneLast4: String?
    public var deadlineAt: String?
    public var createdAt: String
    public var updatedAt: String
    public var decidedAt: String?

    public init(
        id: String,
        familyId: String = "family",
        childMemberId: String = "child",
        childDisplayName: String = "",
        state: String,
        result: String? = nil,
        color: String,
        answeredVia: String? = nil,
        codeChannel: String? = nil,
        gather: String? = nil,
        parentText: String = "",
        transcript: String? = nil,
        claims: Claims? = nil,
        patternId: String? = nil,
        timeline: [String] = [],
        phoneLast4: String? = nil,
        deadlineAt: String? = nil,
        createdAt: String = "2026-11-07T00:00:00+00:00",
        updatedAt: String = "2026-11-07T00:00:00+00:00",
        decidedAt: String? = nil
    ) {
        self.id = id
        self.familyId = familyId
        self.childMemberId = childMemberId
        self.childDisplayName = childDisplayName
        self.state = state
        self.result = result
        self.color = color
        self.answeredVia = answeredVia
        self.codeChannel = codeChannel
        self.gather = gather
        self.parentText = parentText
        self.transcript = transcript
        self.claims = claims
        self.patternId = patternId
        self.timeline = timeline
        self.phoneLast4 = phoneLast4
        self.deadlineAt = deadlineAt
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.decidedAt = decidedAt
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        familyId = try c.decode(String.self, forKey: .familyId)
        childMemberId = try c.decode(String.self, forKey: .childMemberId)
        childDisplayName = try c.decodeIfPresent(String.self, forKey: .childDisplayName) ?? ""
        state = try c.decode(String.self, forKey: .state)
        result = try c.decodeIfPresent(String.self, forKey: .result)
        color = try c.decode(String.self, forKey: .color)
        answeredVia = try c.decodeIfPresent(String.self, forKey: .answeredVia)
        codeChannel = try c.decodeIfPresent(String.self, forKey: .codeChannel)
        gather = try c.decodeIfPresent(String.self, forKey: .gather)
        parentText = try c.decodeIfPresent(String.self, forKey: .parentText) ?? ""
        transcript = try c.decodeIfPresent(String.self, forKey: .transcript)
        claims = try c.decodeIfPresent(Claims.self, forKey: .claims)
        patternId = try c.decodeIfPresent(String.self, forKey: .patternId)
        timeline = try c.decodeIfPresent([String].self, forKey: .timeline) ?? []
        phoneLast4 = try c.decodeIfPresent(String.self, forKey: .phoneLast4)
        deadlineAt = try c.decodeIfPresent(String.self, forKey: .deadlineAt)
        createdAt = try c.decode(String.self, forKey: .createdAt)
        updatedAt = try c.decode(String.self, forKey: .updatedAt)
        decidedAt = try c.decodeIfPresent(String.self, forKey: .decidedAt)
    }
}

public struct CaseList: Codable, Equatable, Sendable {
    public var familyId: String
    public var cases: [CaseSummary]

    public init(familyId: String, cases: [CaseSummary] = []) {
        self.familyId = familyId
        self.cases = cases
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        familyId = try c.decode(String.self, forKey: .familyId)
        cases = try c.decodeIfPresent([CaseSummary].self, forKey: .cases) ?? []
    }
}

public struct CaseSummary: Codable, Equatable, Sendable {
    public var id: String
    public var childMemberId: String
    public var childDisplayName: String
    public var state: String
    public var result: String?
    public var color: String
    public var requestAmount: String?
    public var deadlineAt: String?
    public var createdAt: String
    public var decidedAt: String?

    public init(
        id: String,
        childMemberId: String = "child",
        childDisplayName: String = "",
        state: String,
        result: String? = nil,
        color: String,
        requestAmount: String? = nil,
        deadlineAt: String? = nil,
        createdAt: String,
        decidedAt: String? = nil
    ) {
        self.id = id
        self.childMemberId = childMemberId
        self.childDisplayName = childDisplayName
        self.state = state
        self.result = result
        self.color = color
        self.requestAmount = requestAmount
        self.deadlineAt = deadlineAt
        self.createdAt = createdAt
        self.decidedAt = decidedAt
    }
}

public struct PushRegistration: Codable, Equatable, Sendable {
    public var status: String
    public var provider: String
}

enum JSONCoding {
    static func decode<T: Decodable>(_ type: T.Type, from data: Data) throws -> T {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decode
        }
    }
}
