package com.familyshield.app.domain

import com.familyshield.app.R
import com.familyshield.app.sampleChild
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Instant
import java.util.Locale

class DomainTest {
    @Test
    fun sha256HexIsLowercase() {
        assertEquals(
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            Nonces.sha256Hex("abc"),
        )
    }

    @Test
    fun localeIsKoOnlyForKorean() {
        assertEquals("ko", ApiLocale.of(Locale.KOREAN))
        assertEquals("en", ApiLocale.of(Locale.US))
        assertEquals("en", ApiLocale.of(Locale.JAPAN))
    }

    @Test
    fun phoneAcceptsNanpAndKoreaAndRejectsOthers() {
        assertEquals("+15551234567", (PhoneInput.parse("+1 (555) 123-4567") as PhoneInput.Valid).e164)
        assertEquals("+821012345678", (PhoneInput.parse("+82 010-1234-5678") as PhoneInput.Valid).e164)
        assertTrue(PhoneInput.parse("+44 20 7946 0958") is PhoneInput.UnsupportedCountry)
        assertTrue(PhoneInput.parse("not a number") is PhoneInput.Invalid)
    }

    @Test
    fun verifyIsEnabledOnlyWhenActiveAndConfirmed() {
        val ready = sampleChild(status = "active", confirmedAt = "2026-11-07T00:00:00+00:00")
        assertTrue(MemberRules.canVerify(ready))
        assertEquals(ChildStage.READY, MemberRules.stage(ready))
        val pending = sampleChild(awaitingConfirm = true, linked = true, phoneVerified = true, phoneLast4 = "0123")
        assertFalse(MemberRules.canVerify(pending))
        assertEquals(ChildStage.AWAITING_CONFIRM, MemberRules.stage(pending))
        val expired = sampleChild(inviteExpiresAt = "2020-01-01T00:00:00+00:00")
        assertEquals(ChildStage.INVITE_EXPIRED, MemberRules.stage(expired, Instant.parse("2026-11-07T00:00:00Z")))
        assertFalse(MemberRules.canReissueInvite(sampleChild(callOnly = true, phoneLast4 = "0123")))
        assertTrue(MemberRules.hasPendingNumber(sampleChild(pendingPhoneLast4 = "9999")))
    }

    @Test
    fun everyResultCodeHasCopyAndOnlyTheColorPicksGreenOrRed() {
        assertNull(CaseCopy.result(CaseColor.OPEN, null))
        val green = CaseCopy.result(CaseColor.GREEN, "sent")
        assertEquals(R.string.result_sent, green?.body)
        assertEquals(CaseColor.GREEN, green?.color)
        val red = CaseCopy.result(CaseColor.RED, "not_sent")
        assertEquals(R.string.result_not_sent, red?.body)
        assertTrue(CaseCopy.offersFamilyAlert(CaseColor.RED))
        assertFalse(CaseCopy.offersFamilyAlert(CaseColor.YELLOW))
        val yellow = mapOf(
            ResultCode.WRONG to R.string.result_wrong,
            ResultCode.NO_ANSWER to R.string.result_no_answer,
            ResultCode.NO_NUMBER to R.string.result_no_number,
            ResultCode.CALL_FAILED to R.string.result_call_failed,
            ResultCode.TIMEOUT to R.string.result_timeout,
            ResultCode.UNREACHABLE to R.string.result_unreachable,
            ResultCode.CODE_LOCKED to R.string.result_code_locked,
            ResultCode.NUMBER_RECENT to R.string.result_number_recent,
        )
        yellow.forEach { (code, res) ->
            val copy = CaseCopy.result(CaseColor.YELLOW, code.wire)
            assertEquals(code.wire, res, copy?.body)
        }
        assertEquals(R.string.result_yellow_generic, CaseCopy.result(CaseColor.YELLOW, "sent")?.body)
        assertEquals(R.string.result_yellow_generic, CaseCopy.result(CaseColor.YELLOW, null)?.body)
        ResultCode.entries.forEach { code ->
            assertEquals(code, ResultCode.of(code.wire))
        }
    }

    @Test
    fun timelineAndPatternsCoverTheContract() {
        val known = listOf(
            "start", "push_answered_yes", "push_answered_no", "push_failed", "push_window_elapsed",
            "call_failed", "call_busy", "call_no_answer", "call_ended_before_code", "call_ended_before_answer",
            "code_window_elapsed", "use_static_code", "code_accepted", "static_code_mismatch",
            "code_did_not_match", "one_time_code_expired", "code_rejected", "answer_yes", "answer_no",
            "answer_unclear", "answer_window_elapsed", "phone_number_changed",
        )
        known.forEach { assertTrue(it, CaseCopy.timelineStep(it) != R.string.timeline_unknown) }
        assertEquals(R.string.timeline_unknown, CaseCopy.timelineStep("call_accepted"))
        assertEquals(R.string.pattern_gift_card, CaseCopy.patternLabel("gift_card"))
        assertNull(CaseCopy.patternLabel("none"))
        assertNull(CaseCopy.patternLabel("not-a-pattern"))
        assertEquals(R.string.pattern_line_green, CaseCopy.patternLine(CaseColor.GREEN))
        assertEquals(R.string.pattern_line_info, CaseCopy.patternLine(CaseColor.RED))
    }

    @Test
    fun unknownColorIsNeverGreenOrRed() {
        assertEquals(CaseColor.OPEN, CaseColor.of("purple", decidedAt = null))
        assertEquals(CaseColor.YELLOW, CaseColor.of("purple", decidedAt = "2026-11-07T00:00:00+00:00"))
    }
}
