package com.familyshield.app.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ChildRulesTest {
    @Test
    fun enrollmentSkipsThePhoneOnceTheParentHasConfirmed() {
        assertEquals(ChildRules.Step.PHONE, ChildRules.step("invited", phoneVerified = false, checkCodeSet = false))
        assertEquals(ChildRules.Step.CHECK_CODE, ChildRules.step("invited", phoneVerified = true, checkCodeSet = false))
        assertEquals(ChildRules.Step.WAITING, ChildRules.step("invited", phoneVerified = true, checkCodeSet = true))
        assertEquals(ChildRules.Step.CHECK_CODE, ChildRules.step("active", phoneVerified = false, checkCodeSet = false))
        assertEquals(ChildRules.Step.HOME, ChildRules.step("active", phoneVerified = true, checkCodeSet = true))
    }

    @Test
    fun onlyAnOpenCaseCanBeAnsweredAndOnlyACallShowsTheCode() {
        assertTrue(ChildRules.canAnswer("waiting_push"))
        assertTrue(ChildRules.canAnswer("calling"))
        assertTrue(ChildRules.canAnswer("awaiting_answer"))
        assertFalse(ChildRules.canAnswer("confirmed"))
        assertFalse(ChildRules.canAnswer("not_confirmed"))
        assertTrue(ChildRules.canRevealCode("calling"))
        assertFalse(ChildRules.canRevealCode("waiting_push"))
        assertFalse(ChildRules.isOpen("scam"))
    }

    @Test
    fun inviteAndCodesKeepOnlyTheirDigits() {
        assertEquals("GP9B8GKUDCVN", ChildRules.normalizeInvite("gp9b-8gku dcvn"))
        assertTrue(ChildRules.inviteLooksValid("gp9b-8gku dcvn"))
        assertFalse(ChildRules.inviteLooksValid("IIII-LLLL-OOOO"))
        assertFalse(ChildRules.inviteLooksValid("short"))
        assertEquals("1234", ChildRules.digits("12a34-9", 4))
        assertTrue(ChildRules.checkCodesMatch("2580", "2580"))
        assertFalse(ChildRules.checkCodesMatch("2580", "2581"))
        assertFalse(ChildRules.checkCodesMatch("258", "258"))
        assertTrue(ChildRules.isOtp("123456"))
        assertFalse(ChildRules.isOtp("12345"))
    }

    @Test
    fun strongBiometricIsRequiredWhenTheDeviceHasOne() {
        assertEquals(AuthenticatorChoice.STRONG_OR_DEVICE, BiometricPolicy.choose(30, strongEnrolled = true))
        assertEquals(AuthenticatorChoice.STRONG_OR_DEVICE, BiometricPolicy.choose(36, strongEnrolled = true))
        assertEquals(AuthenticatorChoice.STRONG, BiometricPolicy.choose(29, strongEnrolled = true))
        assertEquals(AuthenticatorChoice.STRONG, BiometricPolicy.choose(28, strongEnrolled = true))
        assertEquals(AuthenticatorChoice.DEVICE_ONLY, BiometricPolicy.choose(33, strongEnrolled = false))
        assertEquals(AuthenticatorChoice.DEVICE_ONLY, BiometricPolicy.choose(26, strongEnrolled = false))
    }

    @Test
    fun aPushCarriesTheCaseIdAndDropsAnyCode() {
        val id = "11111111-1111-4111-8111-111111111111"
        val alert = AlertPayload.moneyRequest(
            mapOf("kind" to "money_request", "case_id" to id, "code" to "654321", "digits" to "2580"),
        )
        assertEquals(id, alert?.caseId)
        assertNull(AlertPayload.moneyRequest(mapOf("kind" to "money_request", "case_id" to "not-a-uuid", "code" to "654321")))
        assertNull(AlertPayload.moneyRequest(mapOf("kind" to "number_change_confirmed", "family_id" to id, "code" to "654321")))
        assertTrue("code" in AlertPayload.SECRET_KEYS)
    }
}
