package com.familyshield.app

import com.familyshield.app.data.CaseRepository
import com.familyshield.app.data.api.ApiClient
import com.familyshield.app.data.api.DevLoginRequest
import com.familyshield.app.data.session.SessionManager
import com.familyshield.app.data.session.TokenStore
import com.familyshield.app.domain.CaseColor
import com.familyshield.app.domain.CaseCopy
import com.familyshield.app.ui.caseflow.CaseViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test
import kotlin.time.Duration.Companion.seconds

/**
 * Drives the app's own client against a local DEV_AUTH backend
 * (`./gradlew testDebugUnitTest -PfsE2eBase=http://127.0.0.1:8000 --tests '*ParentFlowE2eTest'`).
 * Skipped when `-PfsE2eBase` is blank.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class ParentFlowE2eTest {
    private var token: String? = null

    @Before
    fun requireBase() {
        assumeTrue("fs.e2e.base is not set", System.getProperty("fs.e2e.base").orEmpty().isNotBlank())
    }

    @After
    fun resetMain() {
        runCatching { Dispatchers.resetMain() }
    }

    @Test
    fun devParentSeesYellowThenRed() = runBlocking {
        val base = System.getProperty("fs.e2e.base").orEmpty().trimEnd('/')
        val session = SessionManager(object : TokenStore {
            override fun load() = token
            override fun save(token: String) { this@ParentFlowE2eTest.token = token }
            override fun clear() { token = null }
        })
        val api = ApiClient(base, tokens = session, onUnauthorized = { rejected -> session.signOutIfCurrent(rejected) })
        val login = api.devLogin(DevLoginRequest(displayName = "E2E Parent", locale = "en"))
        session.signIn(login.token)
        val me = api.me()
        assertEquals(login.userId, me.userId)
        val family = api.createFamily("E2E")
        val child = api.addChild(family.id, "Mina")
        // A number already stored on this dev database is 409 phone_in_use, so each run draws a new one.
        val phone = "+1" + java.util.concurrent.ThreadLocalRandom.current().nextLong(2_000_000_000L, 9_999_999_999L)
        api.devActivate(child.id, phone)
        api.devSetCheckCode(child.id, "2580", biometricOk = false)
        val cases = CaseRepository(api)
        val opened = cases.open(child.id, "please send money")
        val yellow = drive(api, cases, opened.id, "0000")
        assertEquals("wrong", yellow.result)
        assertEquals(CaseColor.YELLOW, CaseColor.of(yellow.color, yellow.decidedAt))
        assertEquals(R.string.result_wrong, CaseCopy.result(CaseColor.YELLOW, yellow.result)?.body)
        showInViewModel(yellow)

        val second = cases.open(child.id, "another message")
        val calling = waitUntil(cases, second.id) { it.state == "calling" || it.color != "open" }
        if (calling.state == "calling") {
            api.devDigits(calling.id, "2580")
        }
        val red = api.devDigits(calling.id, "2")
        assertEquals("not_sent", red.result)
        assertEquals(CaseColor.RED, CaseColor.of(red.color, red.decidedAt))
        assertEquals(R.string.result_not_sent, CaseCopy.result(CaseColor.RED, red.result)?.body)
        assertEquals(true, CaseCopy.offersFamilyAlert(CaseColor.RED))
        showInViewModel(red)
        assertEquals(true, api.familyCases(family.id).cases.any { it.id == red.id })
    }

    private suspend fun drive(api: ApiClient, cases: CaseRepository, caseId: String, digits: String) =
        api.devDigits(waitUntil(cases, caseId) { it.state == "calling" || it.color != "open" }.id, digits)

    private suspend fun waitUntil(
        cases: CaseRepository,
        caseId: String,
        ready: (com.familyshield.app.data.api.ParentCase) -> Boolean,
    ): com.familyshield.app.data.api.ParentCase {
        val deadline = System.nanoTime() + 20_000_000_000L
        var current = cases.case(caseId)
        while (!ready(current) && System.nanoTime() < deadline) {
            kotlinx.coroutines.delay(300)
            current = cases.case(caseId)
        }
        return current
    }

    private fun showInViewModel(case: com.familyshield.app.data.api.ParentCase) {
        Dispatchers.setMain(UnconfinedTestDispatcher())
        val vm = CaseViewModel(com.familyshield.app.data.CaseSource { case }, case.id, case, pollEvery = 30.seconds)
        vm.setVisible(true)
        assertEquals(case.color, vm.state.value.case?.color)
        assertEquals(case.result, vm.state.value.case?.result)
        vm.setVisible(false)
    }
}
