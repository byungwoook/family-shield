package com.familyshield.app.domain

import androidx.annotation.StringRes
import com.familyshield.app.R

/**
 * The colour the parent sees. The server derives `color` from `state` only;
 * a value this app does not know is never shown as green or red.
 */
enum class CaseColor {
    OPEN, GREEN, RED, YELLOW;

    val isDecided: Boolean get() = this != OPEN

    companion object {
        fun of(wire: String?, decidedAt: String? = null): CaseColor = when (wire) {
            "open" -> OPEN
            "green" -> GREEN
            "red" -> RED
            "yellow" -> YELLOW
            // Unknown: keep waiting while the case is undecided, else the safe colour.
            else -> if (decidedAt == null) OPEN else YELLOW
        }
    }
}

/** Every `result` value in contract §6. */
enum class ResultCode(val wire: String) {
    SENT("sent"),
    NOT_SENT("not_sent"),
    WRONG("wrong"),
    NO_ANSWER("no_answer"),
    NO_NUMBER("no_number"),
    CALL_FAILED("call_failed"),
    TIMEOUT("timeout"),
    UNREACHABLE("unreachable"),
    CODE_LOCKED("code_locked"),
    NUMBER_RECENT("number_recent");

    companion object {
        fun of(wire: String?): ResultCode? = entries.firstOrNull { it.wire == wire }
    }
}

/**
 * The result card for a decided case. [body] takes two format arguments, the
 * child's name and the decided time, in that order (each string uses what it
 * needs). The copy is the table in docs/PRODUCT_REDESIGN.md "Copy the app must
 * not regress", with the Guardian paragraphs for the yellow results it points
 * at. None of it tells the parent to send money.
 */
data class ResultCopy(
    val color: CaseColor,
    @param:StringRes val title: Int,
    @param:StringRes val body: Int,
)

object CaseCopy {

    /** Null while the case is open. Only the colour decides green or red; the result code picks the yellow paragraph. */
    fun result(color: CaseColor, result: String?): ResultCopy? = when (color) {
        CaseColor.OPEN -> null
        CaseColor.GREEN -> ResultCopy(CaseColor.GREEN, R.string.result_title_green, R.string.result_sent)
        CaseColor.RED -> ResultCopy(CaseColor.RED, R.string.result_title_red, R.string.result_not_sent)
        CaseColor.YELLOW -> ResultCopy(CaseColor.YELLOW, R.string.result_title_yellow, yellowBody(ResultCode.of(result)))
    }

    @StringRes
    fun yellowBody(code: ResultCode?): Int = when (code) {
        ResultCode.WRONG -> R.string.result_wrong
        ResultCode.NO_ANSWER -> R.string.result_no_answer
        ResultCode.NO_NUMBER -> R.string.result_no_number
        ResultCode.CALL_FAILED -> R.string.result_call_failed
        ResultCode.TIMEOUT -> R.string.result_timeout
        ResultCode.UNREACHABLE -> R.string.result_unreachable
        ResultCode.CODE_LOCKED -> R.string.result_code_locked
        ResultCode.NUMBER_RECENT -> R.string.result_number_recent
        // sent / not_sent never come with yellow; an unknown code gets the general yellow sentence.
        ResultCode.SENT, ResultCode.NOT_SENT, null -> R.string.result_yellow_generic
    }

    /** The line under "Don't send money yet" while the case is open. Takes the child's name. */
    @StringRes
    fun openLine(state: String): Int = when (state) {
        "waiting_push" -> R.string.open_waiting_push
        "calling" -> R.string.open_calling
        "awaiting_answer" -> R.string.open_awaiting_answer
        else -> R.string.open_starting
    }

    /** Timeline step id (contract §6) to a sentence. An id this app does not know gets a generic line. */
    @StringRes
    fun timelineStep(step: String): Int = TIMELINE[step] ?: R.string.timeline_unknown

    val TIMELINE: Map<String, Int> = mapOf(
        "start" to R.string.timeline_start,
        "push_answered_yes" to R.string.timeline_push_answered_yes,
        "push_answered_no" to R.string.timeline_push_answered_no,
        "push_failed" to R.string.timeline_push_failed,
        "push_window_elapsed" to R.string.timeline_push_window_elapsed,
        "call_failed" to R.string.timeline_call_failed,
        "call_busy" to R.string.timeline_call_busy,
        "call_no_answer" to R.string.timeline_call_no_answer,
        "call_ended_before_code" to R.string.timeline_call_ended_before_code,
        "call_ended_before_answer" to R.string.timeline_call_ended_before_answer,
        "code_window_elapsed" to R.string.timeline_code_window_elapsed,
        "use_static_code" to R.string.timeline_use_static_code,
        "code_accepted" to R.string.timeline_code_accepted,
        "static_code_mismatch" to R.string.timeline_static_code_mismatch,
        "code_did_not_match" to R.string.timeline_code_did_not_match,
        "one_time_code_expired" to R.string.timeline_one_time_code_expired,
        "code_rejected" to R.string.timeline_code_rejected,
        "answer_yes" to R.string.timeline_answer_yes,
        "answer_no" to R.string.timeline_answer_no,
        "answer_unclear" to R.string.timeline_answer_unclear,
        "answer_window_elapsed" to R.string.timeline_answer_window_elapsed,
        "phone_number_changed" to R.string.timeline_phone_number_changed,
    )

    /** backend/patterns.json labels, copied into string resources. `none` and unknown ids have no label. */
    val PATTERN_LABELS: Map<String, Int> = mapOf(
        "fake_arrest_bail" to R.string.pattern_fake_arrest_bail,
        "accident" to R.string.pattern_accident,
        "gift_card" to R.string.pattern_gift_card,
        "crypto_or_wire" to R.string.pattern_crypto_or_wire,
        "secrecy" to R.string.pattern_secrecy,
        "tuition_or_school" to R.string.pattern_tuition_or_school,
        "new_number" to R.string.pattern_new_number,
    )

    @StringRes
    fun patternLabel(patternId: String?): Int? = patternId?.let { PATTERN_LABELS[it] }

    /**
     * The pattern line (the Guardian's `scam_line` rule). Under green it says the
     * message looked like a known pattern but the child confirmed it, and warns
     * about irreversible payments; anywhere else it is information only. It never
     * decides the colour and never says to pay. Format args: label, name.
     */
    @StringRes
    fun patternLine(color: CaseColor): Int =
        if (color == CaseColor.GREEN) R.string.pattern_line_green else R.string.pattern_line_info

    /** Only a red case offers the copyable family warning (`family_alert`). */
    fun offersFamilyAlert(color: CaseColor): Boolean = color == CaseColor.RED
}
