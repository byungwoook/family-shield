package com.familyshield.app.domain

import java.util.Locale

/**
 * Enrollment and answer rules for the child path. This file never holds a
 * check code or a one-time code: those stay in the request that sets them,
 * or on screen until the child hides them.
 */
object ChildRules {
    /** States in which the child can still answer. A terminal state is not in here. */
    val OPEN_STATES = setOf("waiting_push", "calling", "awaiting_answer")

    private val CASE_ID = Regex(
        "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    )

    /** The invite alphabet from the contract (`23456789ABCDEFGHJKMNPQRSTUVWXYZ`). */
    private const val INVITE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"

    enum class Step { PHONE, OTP, CHECK_CODE, WAITING, HOME }

    /**
     * Where the child lands. An `active` membership already passed parent
     * confirm, and confirm requires a verified number, so this install skips
     * the phone step even with no local flag.
     */
    fun step(status: String, phoneVerified: Boolean, checkCodeSet: Boolean): Step {
        val phoneDone = phoneVerified || status == "active"
        if (!phoneDone) return Step.PHONE
        if (!checkCodeSet) return Step.CHECK_CODE
        if (status != "active") return Step.WAITING
        return Step.HOME
    }

    fun isOpen(state: String?): Boolean = state in OPEN_STATES

    /** Yes / No is offered only while the server would still accept it. */
    fun canAnswer(state: String?): Boolean = state in OPEN_STATES

    /** The 6-digit code exists only while the fallback call is asking for it. */
    fun canRevealCode(state: String?): Boolean = state == "calling"

    fun isCaseId(value: String): Boolean = CASE_ID.matches(value)

    /** Spaces and dashes out, uppercased. The server does the same before lookup. */
    fun normalizeInvite(raw: String): String =
        raw.uppercase(Locale.US).replace(Regex("[\\s-]"), "")

    fun inviteLooksValid(raw: String): Boolean {
        val secret = normalizeInvite(raw)
        return secret.length == 12 && secret.all { it in INVITE_ALPHABET }
    }

    fun digits(raw: String, max: Int): String = raw.filter { it.isDigit() }.take(max)

    fun isOtp(code: String): Boolean = code.length == 6 && code.all { it.isDigit() }

    fun isCheckCode(code: String): Boolean = code.length == 4 && code.all { it.isDigit() }

    fun checkCodesMatch(first: String, second: String): Boolean =
        isCheckCode(first) && first == second
}

/**
 * What [androidx.biometric.BiometricPrompt] is allowed to accept.
 * Strong biometrics when the device has them. API 30 and later can offer the
 * device passcode in the same prompt; earlier releases cannot combine the two,
 * so a device with a strong biometric gets only that.
 */
enum class AuthenticatorChoice { STRONG, STRONG_OR_DEVICE, DEVICE_ONLY }

object BiometricPolicy {
    fun choose(sdkInt: Int, strongEnrolled: Boolean): AuthenticatorChoice = when {
        strongEnrolled && sdkInt >= 30 -> AuthenticatorChoice.STRONG_OR_DEVICE
        strongEnrolled -> AuthenticatorChoice.STRONG
        else -> AuthenticatorChoice.DEVICE_ONLY
    }
}
