package com.familyshield.app.ui

import com.familyshield.app.R
import com.familyshield.app.SAMPLE_CASE_ID
import com.familyshield.app.data.ChildProgress
import com.familyshield.app.data.ChildSource
import com.familyshield.app.data.api.ApiException
import com.familyshield.app.data.api.CallCode
import com.familyshield.app.data.api.ChildCase
import com.familyshield.app.data.api.InviteAccepted
import com.familyshield.app.data.api.OtpStarted
import com.familyshield.app.domain.ChildRules
import com.familyshield.app.sampleChildCase
import com.familyshield.app.ui.child.AcceptInviteViewModel
import com.familyshield.app.ui.child.BiometricPurpose
import com.familyshield.app.ui.child.ChildViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ChildFlowTest {
    @Test
    fun notNowLeavesTheCaseOpenAndPostsNothing() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val api = FakeChild()
            val vm = home(api)
            vm.openAlert(SAMPLE_CASE_ID)
            advanceUntilIdle()
            assertEquals("waiting_push", vm.state.value.case?.state)
            vm.notNow()
            advanceUntilIdle()
            assertTrue(api.answers.isEmpty())
            assertEquals("waiting_push", vm.state.value.case?.state)
            assertTrue(ChildRules.isOpen(vm.state.value.case?.state))
            assertFalse(vm.state.value.prompt)
            assertNull(vm.state.value.revealedCode)
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun yesIsPostedOnlyAfterBiometrics() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val api = FakeChild()
            val vm = home(api)
            vm.openAlert(SAMPLE_CASE_ID)
            advanceUntilIdle()
            vm.requestYes()
            assertTrue(api.answers.isEmpty())
            assertEquals(BiometricPurpose.ANSWER_YES, vm.state.value.pendingBiometric)
            vm.onBiometricResult(false)
            advanceUntilIdle()
            assertTrue(api.answers.isEmpty())
            assertEquals("waiting_push", vm.state.value.case?.state)
            vm.requestYes()
            vm.onBiometricResult(true)
            advanceUntilIdle()
            assertEquals(listOf("yes"), api.answers)
            assertEquals("confirmed", vm.state.value.case?.state)
            assertFalse(ChildRules.isOpen(vm.state.value.case?.state))
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun theOneTimeCodeIsShownOnlyAfterBiometricsAndNotStored() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val api = FakeChild(case = sampleChildCase(state = "calling", codeChannel = "one_time"))
            val progress = enrolled()
            val vm = home(api, progress)
            vm.openAlert(SAMPLE_CASE_ID)
            advanceUntilIdle()
            vm.requestReveal()
            assertEquals(0, api.callReads)
            vm.onBiometricResult(false)
            advanceUntilIdle()
            assertEquals(0, api.callReads)
            assertNull(vm.state.value.revealedCode)
            vm.requestReveal()
            vm.onBiometricResult(true)
            advanceUntilIdle()
            assertEquals(1, api.callReads)
            assertEquals("654321", vm.state.value.revealedCode)
            assertFalse(progress.storedValues().any { it.contains("654321") })
            vm.hideCode()
            assertNull(vm.state.value.revealedCode)
            assertFalse(vm.state.value.callFallback)
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun aUsedOneTimeCodeTellsTheChildToUseTheCheckCode() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val api = FakeChild(
                case = sampleChildCase(state = "calling"),
                callCode = CallCode(code = null, fallback = "static"),
            )
            val progress = enrolled()
            val vm = home(api, progress)
            vm.openAlert(SAMPLE_CASE_ID)
            advanceUntilIdle()
            vm.requestReveal()
            vm.onBiometricResult(true)
            advanceUntilIdle()
            assertNull(vm.state.value.revealedCode)
            assertTrue(vm.state.value.callFallback)
            assertFalse(progress.storedValues().any { it.contains("654321") })
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun resettingTheCheckCodeRequiresBiometricsAndSendsTheNewCodeOnce() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val api = FakeChild()
            val progress = enrolled()
            val vm = home(api, progress)
            vm.requestReset()
            vm.onBiometricResult(false)
            advanceUntilIdle()
            assertTrue(api.codes.isEmpty())
            assertFalse(vm.state.value.resetUnlocked)
            vm.requestReset()
            vm.onBiometricResult(true)
            vm.setCode("1357")
            vm.setCodeAgain("9999")
            vm.submitReset()
            advanceUntilIdle()
            assertTrue(api.codes.isEmpty())
            vm.setCodeAgain("1357")
            vm.submitReset()
            advanceUntilIdle()
            assertEquals("1357" to true, api.codes.single())
            assertEquals("", vm.state.value.code)
            assertEquals("", vm.state.value.codeAgain)
            assertFalse(progress.storedValues().any { it.contains("1357") || it.contains("2580") })
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun enrollmentSetsTheCheckCodeWithoutBiometrics() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val api = FakeChild()
            val progress = MemoryProgress()
            val vm = ChildViewModel("m1", "Lee", "invited", api, progress)
            assertEquals(ChildRules.Step.PHONE, vm.state.value.step)
            vm.setPhone("+44 20 7946 0958")
            vm.submitPhone()
            advanceUntilIdle()
            assertTrue(api.otpPhones.isEmpty())
            assertEquals(R.string.error_unsupported_country, vm.state.value.error?.res)
            vm.setPhone("+82 010-1234-5678")
            vm.submitPhone()
            advanceUntilIdle()
            assertEquals("+821012345678", api.otpPhones.single())
            assertEquals(ChildRules.Step.OTP, vm.state.value.step)
            vm.setOtp("12345")
            vm.submitOtp()
            advanceUntilIdle()
            assertEquals(ChildRules.Step.OTP, vm.state.value.step)
            vm.setOtp("123456")
            vm.submitOtp()
            advanceUntilIdle()
            assertEquals(ChildRules.Step.CHECK_CODE, vm.state.value.step)
            assertEquals("", vm.state.value.otp)
            vm.setCode("2580")
            vm.setCodeAgain("2580")
            vm.submitCheckCode()
            advanceUntilIdle()
            assertEquals("2580" to false, api.codes.single())
            assertEquals("", vm.state.value.code)
            assertEquals(ChildRules.Step.WAITING, vm.state.value.step)
            assertFalse(progress.storedValues().any { it.contains("2580") || it.contains("123456") })
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun anExistingCodeIsNotReplacedWithoutBiometrics() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val api = FakeChild()
            api.setError = ApiException.Http(403, "biometric_required")
            val progress = MemoryProgress()
            progress.markPhoneVerified("m1")
            val vm = ChildViewModel("m1", "Lee", "invited", api, progress)
            vm.setCode("2580")
            vm.setCodeAgain("2580")
            vm.submitCheckCode()
            advanceUntilIdle()
            assertEquals("2580" to false, api.codes.single())
            assertEquals("", vm.state.value.code)
            assertTrue(progress.isCheckCodeSet("m1"))
            assertEquals(ChildRules.Step.WAITING, vm.state.value.step)
            assertEquals(R.string.child_code_exists, vm.state.value.notice?.res)
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun aNumberAlreadyOnTheAccountSkipsAhead() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val api = FakeChild()
            api.startError = ApiException.Http(409, "phone_already_set")
            val progress = MemoryProgress()
            val vm = ChildViewModel("m1", "Lee", "invited", api, progress)
            vm.setPhone("+1 555 123 4567")
            vm.submitPhone()
            advanceUntilIdle()
            assertTrue(progress.isPhoneVerified("m1"))
            assertEquals(ChildRules.Step.CHECK_CODE, vm.state.value.step)
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun inviteSecretIsNormalizedAndABadOneIsNotSent() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val api = FakeChild()
            val vm = AcceptInviteViewModel(api)
            vm.setSecret("not a code")
            var accepted = false
            vm.accept { accepted = true }
            advanceUntilIdle()
            assertFalse(accepted)
            assertTrue(api.secrets.isEmpty())
            vm.setSecret("gp9b-8gku dcvn")
            vm.accept { accepted = true }
            advanceUntilIdle()
            assertEquals("GP9B8GKUDCVN", api.secrets.single())
            assertTrue(accepted)
        } finally {
            Dispatchers.resetMain()
        }
    }

    private fun enrolled() = MemoryProgress().apply {
        markPhoneVerified("m1")
        markCheckCodeSet("m1")
    }

    private fun home(api: FakeChild, progress: ChildProgress = enrolled()) =
        ChildViewModel("m1", "Lee", "active", api, progress)
}

private class MemoryProgress : ChildProgress {
    private val phone = mutableSetOf<String>()
    private val code = mutableSetOf<String>()

    override fun isPhoneVerified(memberId: String) = memberId in phone

    override fun isCheckCodeSet(memberId: String) = memberId in code

    override fun markPhoneVerified(memberId: String) {
        phone += memberId
    }

    override fun markCheckCodeSet(memberId: String) {
        code += memberId
    }

    override fun storedValues(): List<String> = (phone + code).map { "flag:$it" }
}

private class FakeChild(
    var case: ChildCase = sampleChildCase(),
    var callCode: CallCode = CallCode(code = "654321"),
) : ChildSource {
    val answers = mutableListOf<String>()
    val codes = mutableListOf<Pair<String, Boolean>>()
    val otpPhones = mutableListOf<String>()
    val secrets = mutableListOf<String>()
    var callReads = 0
    var startError: ApiException? = null
    var setError: ApiException? = null

    override suspend fun acceptInvite(secret: String): InviteAccepted {
        secrets += secret
        return InviteAccepted("m1", "fam", "Mina", "invited")
    }

    override suspend fun startOtp(phoneE164: String, channel: String, biometricOk: Boolean): OtpStarted {
        startError?.let { throw it }
        otpPhones += phoneE164
        return OtpStarted("sent", channel, "5678", "2026-11-07T00:10:00+00:00")
    }

    override suspend fun checkOtp(phoneE164: String, code: String) = Unit

    override suspend fun setCheckCode(code: String, biometricOk: Boolean) {
        codes += code to biometricOk
        setError?.let { throw it }
    }

    override suspend fun loadCase(caseId: String): ChildCase = case

    override suspend fun answer(caseId: String, answer: String): ChildCase {
        answers += answer
        val yes = answer == "yes"
        return case.copy(
            state = if (yes) "confirmed" else "scam",
            result = if (yes) "sent" else "not_sent",
            color = if (yes) "green" else "red",
            answeredVia = "push",
            decidedAt = "2026-11-07T00:02:00+00:00",
        )
    }

    override suspend fun callCode(caseId: String): CallCode {
        callReads += 1
        return callCode
    }
}
