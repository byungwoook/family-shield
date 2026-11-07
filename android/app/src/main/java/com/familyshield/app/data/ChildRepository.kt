package com.familyshield.app.data

import android.content.SharedPreferences
import com.familyshield.app.data.api.ApiClient
import com.familyshield.app.data.api.CallCode
import com.familyshield.app.data.api.CheckCodeRequest
import com.familyshield.app.data.api.ChildCase
import com.familyshield.app.data.api.InviteAccepted
import com.familyshield.app.data.api.OtpCheckRequest
import com.familyshield.app.data.api.OtpStartRequest
import com.familyshield.app.data.api.OtpStarted

/** The child calls. Nothing here remembers a code after the call returns. */
interface ChildSource {
    suspend fun acceptInvite(secret: String): InviteAccepted
    suspend fun startOtp(phoneE164: String, channel: String, biometricOk: Boolean): OtpStarted
    suspend fun checkOtp(phoneE164: String, code: String)
    suspend fun setCheckCode(code: String, biometricOk: Boolean)
    suspend fun loadCase(caseId: String): ChildCase
    suspend fun answer(caseId: String, answer: String): ChildCase
    suspend fun callCode(caseId: String): CallCode
}

class ChildRepository(private val api: ApiClient) : ChildSource {
    override suspend fun acceptInvite(secret: String): InviteAccepted = api.acceptInvite(secret)

    override suspend fun startOtp(phoneE164: String, channel: String, biometricOk: Boolean): OtpStarted =
        api.startOtp(OtpStartRequest(phoneE164, channel, biometricOk))

    override suspend fun checkOtp(phoneE164: String, code: String) {
        api.checkOtp(OtpCheckRequest(phoneE164, code))
    }

    override suspend fun setCheckCode(code: String, biometricOk: Boolean) {
        api.setCheckCode(CheckCodeRequest(code, biometricOk))
    }

    override suspend fun loadCase(caseId: String): ChildCase = api.childCase(caseId)

    override suspend fun answer(caseId: String, answer: String): ChildCase = api.answerCase(caseId, answer)

    override suspend fun callCode(caseId: String): CallCode = api.callCode(caseId)
}

/**
 * Which enrollment steps this install has finished, per member. Booleans only:
 * never the phone number, the SMS code, the check code, or the one-time code.
 */
interface ChildProgress {
    fun isPhoneVerified(memberId: String): Boolean
    fun isCheckCodeSet(memberId: String): Boolean
    fun markPhoneVerified(memberId: String)
    fun markCheckCodeSet(memberId: String)

    /** Every stored value, so a test can show a code was not written. */
    fun storedValues(): List<String>
}

class PrefsChildProgress(private val prefs: SharedPreferences) : ChildProgress {
    override fun isPhoneVerified(memberId: String): Boolean = prefs.getBoolean(phoneKey(memberId), false)

    override fun isCheckCodeSet(memberId: String): Boolean = prefs.getBoolean(codeKey(memberId), false)

    override fun markPhoneVerified(memberId: String) {
        prefs.edit().putBoolean(phoneKey(memberId), true).apply()
    }

    override fun markCheckCodeSet(memberId: String) {
        prefs.edit().putBoolean(codeKey(memberId), true).apply()
    }

    override fun storedValues(): List<String> = prefs.all.values.map { it.toString() }

    private fun phoneKey(memberId: String) = "phone_verified_$memberId"

    private fun codeKey(memberId: String) = "check_code_set_$memberId"

    companion object {
        const val PREFS = "child_progress"
    }
}
