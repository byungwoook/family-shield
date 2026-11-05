package com.familyshield.app.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Wire types for docs/API_CONTRACT.md. Field names follow the contract exactly
// (@SerialName); unknown response fields are ignored by ApiJson. Request bodies
// carry only documented fields, because the server rejects extras (400 invalid_body).
// Enum-like values (state, result, color, role, status) stay strings here and are
// read through domain helpers, so a new server value never breaks parsing.

// ---------- Auth ----------

@Serializable
data class NonceResponse(
    val nonce: String,
    @SerialName("expires_at") val expiresAt: String,
)

@Serializable
data class GoogleSignInRequest(
    @SerialName("id_token") val idToken: String,
    /** The raw nonce from /v1/auth/nonce, not its hash. */
    val nonce: String,
    val locale: String,
    @SerialName("display_name") val displayName: String? = null,
)

@Serializable
data class SessionResponse(
    val token: String,
    @SerialName("user_id") val userId: String,
)

@Serializable
data class DevLoginRequest(
    @SerialName("display_name") val displayName: String,
    val locale: String,
    @SerialName("auth_subject") val authSubject: String? = null,
)

@Serializable
data class DevLoginResponse(
    val token: String,
    @SerialName("user_id") val userId: String,
    @SerialName("auth_subject") val authSubject: String,
)

// ---------- Me ----------

@Serializable
data class Me(
    @SerialName("user_id") val userId: String,
    @SerialName("display_name") val displayName: String = "",
    val locale: String = "en",
    val memberships: List<Membership> = emptyList(),
)

@Serializable
data class Membership(
    @SerialName("member_id") val memberId: String,
    @SerialName("family_id") val familyId: String,
    @SerialName("family_name") val familyName: String = "",
    val role: String,
    val status: String,
    @SerialName("display_name") val displayName: String = "",
)

// ---------- Family and members ----------

@Serializable
data class CreateFamilyRequest(val name: String)

@Serializable
data class FamilyCreated(val id: String, val name: String)

@Serializable
data class AddChildRequest(@SerialName("display_name") val displayName: String)

@Serializable
data class ChildInvite(
    val id: String,
    @SerialName("display_name") val displayName: String,
    val status: String,
    @SerialName("invite_secret") val inviteSecret: String,
    @SerialName("invite_expires_at") val inviteExpiresAt: String,
)

@Serializable
data class InviteReissued(
    val id: String,
    @SerialName("invite_secret") val inviteSecret: String,
    @SerialName("invite_expires_at") val inviteExpiresAt: String,
)

@Serializable
data class Roster(
    @SerialName("family_id") val familyId: String,
    val members: List<Member> = emptyList(),
)

@Serializable
data class Member(
    val id: String,
    val role: String,
    @SerialName("display_name") val displayName: String = "",
    val status: String,
    val linked: Boolean = false,
    @SerialName("phone_last4") val phoneLast4: String? = null,
    @SerialName("pending_phone_last4") val pendingPhoneLast4: String? = null,
    @SerialName("phone_verified") val phoneVerified: Boolean = false,
    @SerialName("has_check_code") val hasCheckCode: Boolean = false,
    @SerialName("awaiting_confirm") val awaitingConfirm: Boolean = false,
    @SerialName("invite_expires_at") val inviteExpiresAt: String? = null,
    @SerialName("call_only") val callOnly: Boolean = false,
    @SerialName("allow_link_open") val allowLinkOpen: Boolean = false,
    @SerialName("confirmed_at") val confirmedAt: String? = null,
)

@Serializable
data class DecisionRequest(val decision: String)

/** POST .../confirm: `{id, status:"active", phone_last4}` or `{id, status:"removed"}`. */
@Serializable
data class MemberDecision(
    val id: String,
    val status: String,
    @SerialName("phone_last4") val phoneLast4: String? = null,
)

/** POST .../phone-change: `{id, status:"changed", phone_last4, cancelled_cases}` or `{id, status:"kept"}`. */
@Serializable
data class PhoneChangeDecision(
    val id: String,
    val status: String,
    @SerialName("phone_last4") val phoneLast4: String? = null,
    @SerialName("cancelled_cases") val cancelledCases: Int? = null,
)

@Serializable
data class PhoneRequest(@SerialName("phone_e164") val phoneE164: String)

/** POST .../call-only and .../allow-link (202). */
@Serializable
data class LinkSent(
    val status: String,
    @SerialName("phone_last4") val phoneLast4: String? = null,
)

// ---------- Cases ----------

@Serializable
data class CreateCaseRequest(
    @SerialName("child_member_id") val childMemberId: String,
    val text: String = "",
)

@Serializable
data class Claims(
    @SerialName("claimed_identity") val claimedIdentity: String? = null,
    val amount: String? = null,
    val story: String? = null,
    @SerialName("red_flags") val redFlags: List<String> = emptyList(),
)

/** The parent case body (contract §6). */
@Serializable
data class ParentCase(
    val id: String,
    @SerialName("family_id") val familyId: String,
    @SerialName("child_member_id") val childMemberId: String,
    @SerialName("child_display_name") val childDisplayName: String = "",
    val state: String,
    val result: String? = null,
    val color: String,
    @SerialName("answered_via") val answeredVia: String? = null,
    @SerialName("code_channel") val codeChannel: String? = null,
    val gather: String? = null,
    @SerialName("parent_text") val parentText: String = "",
    val transcript: String? = null,
    val claims: Claims? = null,
    @SerialName("pattern_id") val patternId: String? = null,
    val timeline: List<String> = emptyList(),
    @SerialName("phone_last4") val phoneLast4: String? = null,
    @SerialName("deadline_at") val deadlineAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
    @SerialName("decided_at") val decidedAt: String? = null,
)

@Serializable
data class CaseList(
    @SerialName("family_id") val familyId: String,
    val cases: List<CaseSummary> = emptyList(),
)

@Serializable
data class CaseSummary(
    val id: String,
    @SerialName("child_member_id") val childMemberId: String,
    @SerialName("child_display_name") val childDisplayName: String = "",
    val state: String,
    val result: String? = null,
    val color: String,
    @SerialName("created_at") val createdAt: String,
    @SerialName("decided_at") val decidedAt: String? = null,
)

// ---------- Child side (used by the child path, milestone 14) ----------

@Serializable
data class AcceptInviteRequest(val secret: String)

@Serializable
data class InviteAccepted(
    @SerialName("member_id") val memberId: String,
    @SerialName("family_id") val familyId: String,
    @SerialName("display_name") val displayName: String,
    val status: String,
)

@Serializable
data class OtpStartRequest(
    @SerialName("phone_e164") val phoneE164: String,
    val channel: String = "sms",
    @SerialName("biometric_ok") val biometricOk: Boolean = false,
)

@Serializable
data class OtpStarted(
    val status: String,
    val channel: String,
    @SerialName("phone_last4") val phoneLast4: String,
    @SerialName("expires_at") val expiresAt: String,
)

@Serializable
data class OtpCheckRequest(
    @SerialName("phone_e164") val phoneE164: String,
    val code: String,
)

@Serializable
data class OtpChecked(
    val status: String,
    @SerialName("phone_last4") val phoneLast4: String,
)

@Serializable
data class CheckCodeRequest(
    val code: String,
    @SerialName("biometric_ok") val biometricOk: Boolean,
)

@Serializable
data class StatusResponse(val status: String)

@Serializable
data class PushTokenRequest(
    val provider: String,
    val token: String,
    val env: String? = null,
    val locale: String,
)

@Serializable
data class PushTokenRegistered(val status: String, val provider: String)

@Serializable
data class AnswerRequest(val answer: String)

/** The child case body (`CHILD_CASE_KEYS`): no text, names, phone, or timeline. */
@Serializable
data class ChildCase(
    val id: String,
    @SerialName("child_member_id") val childMemberId: String,
    val kind: String = "money_request",
    val state: String,
    val result: String? = null,
    val color: String,
    @SerialName("answered_via") val answeredVia: String? = null,
    @SerialName("code_channel") val codeChannel: String? = null,
    val gather: String? = null,
    @SerialName("deadline_at") val deadlineAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
    @SerialName("decided_at") val decidedAt: String? = null,
)

/** GET /v1/cases/{id}/call-code: `{"code": "123456"}` or `{"code": null, "fallback": "static"}`. */
@Serializable
data class CallCode(
    val code: String? = null,
    val fallback: String? = null,
)

// ---------- DEV_AUTH helpers (debug builds and the e2e test only) ----------

@Serializable
data class DevActivateRequest(
    @SerialName("phone_e164") val phoneE164: String,
    @SerialName("user_id") val userId: String? = null,
)

@Serializable
data class DevActivated(
    val status: String,
    @SerialName("phone_last4") val phoneLast4: String,
)

@Serializable
data class DigitsRequest(val digits: String)

/** Error body for every `/v1/*` error: `{"error": "<code>"}`. Framework 404/405 send `detail`. */
@Serializable
internal data class ErrorBody(
    val error: String? = null,
    val detail: String? = null,
)
