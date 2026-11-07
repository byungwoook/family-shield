package com.familyshield.app.domain

/** The only push the child answers. The code is never part of it. */
data class MoneyRequestAlert(val caseId: String)

object AlertPayload {
    const val EXTRA_KIND = "kind"
    const val EXTRA_CASE_ID = "case_id"
    const val KIND_MONEY_REQUEST = "money_request"

    /**
     * Keys that must not be copied onto a notification or a tap intent.
     * A payload that includes one is still a valid alert; the value is dropped.
     */
    val SECRET_KEYS = setOf("code", "otp", "check_code", "one_time_code", "digits", "nonce")

    fun moneyRequest(data: Map<String, String>): MoneyRequestAlert? {
        if (data[EXTRA_KIND] != KIND_MONEY_REQUEST) return null
        val id = data[EXTRA_CASE_ID] ?: return null
        if (!ChildRules.isCaseId(id)) return null
        return MoneyRequestAlert(id)
    }
}
