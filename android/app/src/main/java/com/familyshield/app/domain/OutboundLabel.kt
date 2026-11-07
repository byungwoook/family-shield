package com.familyshield.app.domain

/**
 * One label for the number Family Shield calls from.
 * The label is always "Family Shield". A different number, including the
 * child's, is not announced. This is not a list of scam numbers, and it does
 * not decide that a caller is genuine.
 *
 * The same rules live in ios/FamilyShieldCore OutboundIdentification.
 */
object OutboundLabel {
    const val LABEL = "Family Shield"

    /** Reserved fictional NANP number (555-0100). Not a Twilio account. */
    const val PLACEHOLDER_E164 = "+15555550100"

    data class Plan(
        val disallowCall: Boolean = false,
        val rejectCall: Boolean = false,
        val silenceCall: Boolean = false,
        val skipCallLog: Boolean = false,
        val skipNotification: Boolean = false,
        val announceFamilyShield: Boolean,
    )

    /**
     * Zero or one number. A list, a blank, or anything that is not one E.164
     * value yields nothing. Call Directory on iOS wants ascending order; one
     * number already satisfies that.
     */
    fun identificationNumber(configured: String): Long? = singleE164(configured)

    /** Every call is allowed to ring. [Plan.announceFamilyShield] is true only for [configured]. */
    fun plan(incoming: String?, configured: String): Plan {
        return Plan(announceFamilyShield = sameNumber(incoming, configured))
    }

    private val e164 = Regex("""^\+[1-9][0-9]{6,14}$""")

    fun singleE164(configured: String): Long? {
        val trimmed = configured.trim()
        if (trimmed.isEmpty()) return null
        if (trimmed.any { it.isWhitespace() || it == ',' || it == ';' }) return null
        if (!e164.matches(trimmed)) return null
        return trimmed.drop(1).toLongOrNull()
    }

    private fun sameNumber(incoming: String?, configured: String): Boolean {
        val ours = singleE164(configured) ?: return false
        if (incoming == null) return false
        return digits(incoming) == ours
    }

    private fun digits(raw: String): Long? {
        val trimmed = raw.trim()
        if (trimmed.count { it == '+' } > 1) return null
        val only = trimmed.filter { it in '0'..'9' }
        if (only.length !in 7..15 || only.startsWith('0')) return null
        return only.toLongOrNull()
    }
}
