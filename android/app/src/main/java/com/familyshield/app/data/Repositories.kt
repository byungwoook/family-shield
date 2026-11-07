package com.familyshield.app.data

import com.familyshield.app.data.api.ApiClient
import com.familyshield.app.data.api.ApiClient.Decision
import com.familyshield.app.data.api.CaseSummary
import com.familyshield.app.data.api.ChildInvite
import com.familyshield.app.data.api.DevLoginRequest
import com.familyshield.app.data.api.FamilyCreated
import com.familyshield.app.data.api.GoogleSignInRequest
import com.familyshield.app.data.api.InviteReissued
import com.familyshield.app.data.api.LinkSent
import com.familyshield.app.data.api.Me
import com.familyshield.app.data.api.Member
import com.familyshield.app.data.api.MemberDecision
import com.familyshield.app.data.api.ParentCase
import com.familyshield.app.data.api.PhoneChangeDecision
import com.familyshield.app.data.session.SessionManager
import com.familyshield.app.domain.Nonces
import java.util.concurrent.ConcurrentHashMap

/** The raw nonce goes to our server; its SHA-256 hex goes to Google. */
class SignInNonce(val raw: String, val hashed: String)

class AuthRepository(
    private val api: ApiClient,
    private val session: SessionManager,
) {
    /** A fresh nonce for every Google attempt (contract §3). */
    suspend fun newNonce(): SignInNonce {
        val raw = api.nonce().nonce
        return SignInNonce(raw = raw, hashed = Nonces.sha256Hex(raw))
    }

    suspend fun signInWithGoogle(idToken: String, nonce: SignInNonce, locale: String, displayName: String?) {
        val session = api.signInWithGoogle(
            GoogleSignInRequest(
                idToken = idToken,
                nonce = nonce.raw,
                locale = locale,
                displayName = displayName?.trim()?.take(NAME_LIMIT)?.takeIf { it.isNotEmpty() },
            ),
        )
        this.session.signIn(session.token)
    }

    /** DEV_AUTH backends only (debug builds). A new user every time. */
    suspend fun devSignIn(displayName: String, locale: String) {
        val login = api.devLogin(DevLoginRequest(displayName = displayName.trim(), locale = locale))
        session.signIn(login.token)
    }

    suspend fun me(): Me = api.me()

    fun signOut() = session.signOut()

    companion object {
        const val NAME_LIMIT = 200
    }
}

/** What the family screen needs: members, recent cases, and the parent's member actions. */
interface FamilySource {
    suspend fun members(familyId: String): List<Member>
    suspend fun recentCases(familyId: String): List<CaseSummary>
    suspend fun addChild(familyId: String, displayName: String): ChildInvite
    suspend fun reissueInvite(familyId: String, memberId: String): InviteReissued
    suspend fun decideJoin(familyId: String, memberId: String, decision: Decision): MemberDecision
    suspend fun decidePhoneChange(familyId: String, memberId: String, decision: Decision): PhoneChangeDecision
    suspend fun addCallOnly(familyId: String, memberId: String, phoneE164: String): LinkSent
}

class FamilyRepository(private val api: ApiClient) : FamilySource {
    suspend fun createFamily(name: String): FamilyCreated = api.createFamily(name.trim())

    override suspend fun members(familyId: String): List<Member> = api.members(familyId).members

    override suspend fun recentCases(familyId: String): List<CaseSummary> =
        api.familyCases(familyId, limit = RECENT_CASES).cases

    override suspend fun addChild(familyId: String, displayName: String): ChildInvite =
        api.addChild(familyId, displayName.trim())

    override suspend fun reissueInvite(familyId: String, memberId: String): InviteReissued =
        api.reissueInvite(familyId, memberId)

    override suspend fun decideJoin(familyId: String, memberId: String, decision: Decision): MemberDecision =
        api.confirmMember(familyId, memberId, decision)

    override suspend fun decidePhoneChange(familyId: String, memberId: String, decision: Decision): PhoneChangeDecision =
        api.decidePhoneChange(familyId, memberId, decision)

    override suspend fun addCallOnly(familyId: String, memberId: String, phoneE164: String): LinkSent =
        api.addCallOnly(familyId, memberId, phoneE164)

    companion object {
        const val RECENT_CASES = 20
    }
}

/** Reading one case, for the polling screen. */
fun interface CaseSource {
    suspend fun case(caseId: String): ParentCase
}

/** Opening a case as well as reading it. */
interface CaseGateway : CaseSource {
    suspend fun open(childMemberId: String, text: String): ParentCase
}

class CaseRepository(private val api: ApiClient) : CaseGateway {
    // The last body seen per case, so the case screen can draw at once after POST /v1/cases.
    private val lastSeen = ConcurrentHashMap<String, ParentCase>()

    override suspend fun open(childMemberId: String, text: String): ParentCase =
        api.openCase(childMemberId, text.take(TEXT_LIMIT)).also { lastSeen[it.id] = it }

    override suspend fun case(caseId: String): ParentCase =
        api.case(caseId).also { lastSeen[it.id] = it }

    fun cached(caseId: String): ParentCase? = lastSeen[caseId]

    /** On sign-out: nothing from the previous session stays in memory. */
    fun clear() = lastSeen.clear()

    companion object {
        /** The server's limit for `text` (contract §5, POST /v1/cases). */
        const val TEXT_LIMIT = 8000
    }
}
