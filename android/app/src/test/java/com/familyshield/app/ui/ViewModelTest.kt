package com.familyshield.app.ui

import com.familyshield.app.R
import com.familyshield.app.data.CaseGateway
import com.familyshield.app.data.CaseSource
import com.familyshield.app.data.FamilySource
import com.familyshield.app.data.PushApi
import com.familyshield.app.data.PushRegistrar
import com.familyshield.app.data.PushTokenSource
import com.familyshield.app.data.api.ApiClient
import com.familyshield.app.data.api.ApiException
import com.familyshield.app.data.api.CaseSummary
import com.familyshield.app.data.api.ChildInvite
import com.familyshield.app.data.api.InviteReissued
import com.familyshield.app.data.api.LinkSent
import com.familyshield.app.data.api.Me
import com.familyshield.app.data.api.Member
import com.familyshield.app.data.api.MemberDecision
import com.familyshield.app.data.api.Membership
import com.familyshield.app.data.api.ParentCase
import com.familyshield.app.data.api.PhoneChangeDecision
import com.familyshield.app.data.api.PushTokenRequest
import com.familyshield.app.sampleCase
import com.familyshield.app.ui.caseflow.CaseViewModel
import com.familyshield.app.ui.common.ErrorMessages
import com.familyshield.app.ui.family.FamilyViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.time.Duration.Companion.seconds

@OptIn(ExperimentalCoroutinesApi::class)
class ViewModelTest {
    @Test
    fun pollingStopsWhenTheCaseIsDecidedAndWhenHidden() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            var calls = 0
            val source = CaseSource {
                calls += 1
                if (calls < 2) sampleCase(color = "open", state = "calling")
                else sampleCase(color = "yellow", result = "wrong", state = "not_confirmed", decidedAt = "2026-11-07T00:03:00+00:00")
            }
            val vm = CaseViewModel(source, "case-1", pollEvery = 3.seconds)
            vm.setVisible(true)
            advanceUntilIdle()
            assertEquals(2, calls)
            assertEquals("yellow", vm.state.value.case?.color)
            advanceTimeBy(30.seconds)
            assertEquals(2, calls)

            var openCalls = 0
            val open = CaseViewModel(CaseSource {
                openCalls += 1
                sampleCase()
            }, "case-2", pollEvery = 3.seconds)
            open.setVisible(true)
            runCurrent()
            assertEquals(1, openCalls)
            open.setVisible(false)
            advanceTimeBy(30.seconds)
            assertEquals(1, openCalls)
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun pollingStopsOn401() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            var calls = 0
            val vm = CaseViewModel(CaseSource {
                calls += 1
                throw ApiException.Http(401, "unauthorized")
            }, "case-1", pollEvery = 3.seconds)
            vm.setVisible(true)
            runCurrent()
            advanceTimeBy(30.seconds)
            assertEquals(1, calls)
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun openingACaseSurfacesCallableErrorsInsteadOfACase() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val families = FakeFamilies(members = emptyList())
            val gateway = object : CaseGateway {
                override suspend fun open(childMemberId: String, text: String): ParentCase {
                    throw ApiException.Http(400, "member_not_callable")
                }
                override suspend fun case(caseId: String) = sampleCase()
            }
            val vm = FamilyViewModel("fam-1", families, gateway)
            advanceUntilIdle()
            vm.selectChild("child-1")
            var opened = false
            vm.verify { opened = true }
            advanceUntilIdle()
            assertTrue(!opened)
            assertEquals(R.string.error_member_not_callable, vm.state.value.error?.res)
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun addChildRemembersTheInviteSecretOnce() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val families = FakeFamilies(members = emptyList())
            val vm = FamilyViewModel("fam-1", families, object : CaseGateway {
                override suspend fun open(childMemberId: String, text: String) = sampleCase()
                override suspend fun case(caseId: String) = sampleCase()
            })
            advanceUntilIdle()
            vm.setAddName("Mina")
            vm.addChild()
            advanceUntilIdle()
            assertEquals("ABCD-EFGH-JKLM", vm.state.value.invite?.secret)
            vm.dismissInvite()
            assertNull(vm.state.value.invite)
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun rootRoutesParentChildAndEmpty() {
        assertTrue(RootViewModel.route(Me("u", "Ada", "en", emptyList())) is RootState.NeedsFamily)
        val parent = RootViewModel.route(
            Me("u", "Ada", "ko", listOf(Membership("m", "fam", "Lee", "parent", "active", "Ada"))),
        )
        assertTrue(parent is RootState.Parent)
        assertEquals("fam", (parent as RootState.Parent).familyId)
        assertTrue(
            RootViewModel.route(
                Me("u", "Mina", "en", listOf(Membership("m", "fam", "Lee", "child", "active", "Mina"))),
            ) is RootState.Child,
        )
    }

    @Test
    fun pushRegistrationPostsFcmAndSkipsAMissingToken() = runTest {
        val posted = mutableListOf<PushTokenRequest>()
        val api = PushApi { posted += it }
        PushRegistrar(api, PushTokenSource { "  fcm-token  " }).register("ko")
        assertEquals("fcm", posted.single().provider)
        assertEquals("fcm-token", posted.single().token)
        assertNull(posted.single().env)
        assertEquals("ko", posted.single().locale)
        PushRegistrar(api, PushTokenSource { null }).register("en")
        assertEquals(1, posted.size)
    }

    @Test
    fun errorCodesMapToSentences() {
        assertEquals(R.string.error_unsupported_country, ErrorMessages.forCode(400, "unsupported_country"))
        assertEquals(R.string.error_rate_limited, ErrorMessages.forCode(429, "rate_limited"))
        assertEquals(R.string.error_member_not_callable, ErrorMessages.forCode(400, "member_not_callable"))
        assertEquals(R.string.error_network, ErrorMessages.resOf(ApiException.Network(java.io.IOException("down"))))
    }
}

private class FakeFamilies(private val members: List<Member>) : FamilySource {
    override suspend fun members(familyId: String) = members
    override suspend fun recentCases(familyId: String): List<CaseSummary> = emptyList()
    override suspend fun addChild(familyId: String, displayName: String) = ChildInvite(
        id = "child-1",
        displayName = displayName,
        status = "invited",
        inviteSecret = "ABCD-EFGH-JKLM",
        inviteExpiresAt = "2026-11-08T00:00:00+00:00",
    )
    override suspend fun reissueInvite(familyId: String, memberId: String) = InviteReissued("child-1", "NEW", "2026-11-08T00:00:00+00:00")
    override suspend fun decideJoin(familyId: String, memberId: String, decision: ApiClient.Decision) =
        MemberDecision(memberId, "active", "0123")
    override suspend fun decidePhoneChange(familyId: String, memberId: String, decision: ApiClient.Decision) =
        PhoneChangeDecision(memberId, "kept")
    override suspend fun addCallOnly(familyId: String, memberId: String, phoneE164: String) = LinkSent("link_sent", "5678")
}
