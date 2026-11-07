package com.familyshield.app.ui

import androidx.lifecycle.SavedStateHandle
import com.familyshield.app.R
import com.familyshield.app.data.CaseGateway
import com.familyshield.app.data.FamilySource
import com.familyshield.app.data.api.ApiClient
import com.familyshield.app.data.api.CaseAudio
import com.familyshield.app.data.api.CaseSummary
import com.familyshield.app.data.api.ChildInvite
import com.familyshield.app.data.api.InviteReissued
import com.familyshield.app.data.api.LinkSent
import com.familyshield.app.data.api.Member
import com.familyshield.app.data.api.MemberDecision
import com.familyshield.app.data.api.ParentCase
import com.familyshield.app.data.api.PhoneChangeDecision
import com.familyshield.app.domain.ShareProblem
import com.familyshield.app.domain.VoiceNotes
import com.familyshield.app.sampleCase
import com.familyshield.app.ui.family.DraftAudio
import com.familyshield.app.ui.family.FamilyPage
import com.familyshield.app.ui.family.FamilyViewModel
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
import java.io.File
import java.io.RandomAccessFile

@OptIn(ExperimentalCoroutinesApi::class)
class ShareDraftTest {
    @Test
    fun aShareStaysLocalUntilVerifyUploadsIt() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val gateway = RecordingGateway()
            val file = File.createTempFile("note", ".m4a").apply { writeBytes(byteArrayOf(1, 2, 3, 4)) }
            val vm = FamilyViewModel("fam-1", idleFamilies(), gateway)
            advanceUntilIdle()
            vm.applyShare("용돈", DraftAudio(file, "voice.m4a", "audio/mp4"), problem = null, token = "t1")
            advanceUntilIdle()
            assertEquals(0, gateway.opens)
            assertEquals(FamilyPage.NewCase, vm.state.value.page)
            assertEquals("용돈", vm.state.value.caseText)
            assertTrue(vm.state.value.fromShare)
            vm.setCaseText("용돈 부탁")
            vm.applyShare("용돈", DraftAudio(file, "voice.m4a", "audio/mp4"), null, "t1")
            assertEquals("용돈 부탁", vm.state.value.caseText)
            vm.selectChild("child-1")
            var opened = false
            vm.verify { opened = true }
            advanceUntilIdle()
            assertTrue(opened)
            assertEquals(1, gateway.opens)
            assertEquals("용돈 부탁", gateway.lastText)
            assertEquals("audio/mp4", gateway.lastAudio?.contentType)
            assertEquals("voice.m4a", gateway.lastAudio?.uploadName)
            assertFalse(file.exists())
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun anOversizedOrEmptyNoteIsNotUploaded() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val gateway = RecordingGateway()
            val vm = FamilyViewModel("fam-1", idleFamilies(), gateway)
            advanceUntilIdle()
            val big = File.createTempFile("big", ".m4a")
            RandomAccessFile(big, "rw").use { it.setLength(VoiceNotes.MAX_BYTES + 1) }
            vm.applyShare("", DraftAudio(big, "big.m4a", "audio/mp4"), null, "big")
            vm.selectChild("child-1")
            vm.verify { }
            advanceUntilIdle()
            assertEquals(0, gateway.opens)
            assertEquals(R.string.share_audio_too_large, vm.state.value.error?.res)
            big.delete()

            val empty = File.createTempFile("empty", ".m4a")
            vm.applyShare("", DraftAudio(empty, "empty.m4a", "audio/mp4"), null, "empty")
            vm.selectChild("child-1")
            vm.verify { }
            advanceUntilIdle()
            assertEquals(0, gateway.opens)
            assertEquals(R.string.share_audio_empty, vm.state.value.error?.res)
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun removingTheNoteSendsTextOnly() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val gateway = RecordingGateway()
            val file = File.createTempFile("note", ".ogg").apply { writeBytes(byteArrayOf(1)) }
            val vm = FamilyViewModel("fam-1", idleFamilies(), gateway)
            advanceUntilIdle()
            vm.applyShare("hello", DraftAudio(file, "n.ogg", "audio/ogg"), null, "t")
            vm.removeDraftAudio()
            assertNull(vm.state.value.draftAudio)
            assertFalse(file.exists())
            vm.selectChild("child-1")
            vm.verify { }
            advanceUntilIdle()
            assertNull(gateway.lastAudio)
            assertEquals("hello", gateway.lastText)
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun aRejectedShareDoesNotUploadAndKeepsTheText() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val gateway = RecordingGateway()
            val vm = FamilyViewModel("fam-1", idleFamilies(), gateway)
            advanceUntilIdle()
            vm.applyShare("pasted", audio = null, problem = ShareProblem.UNSUPPORTED, token = "bad")
            advanceUntilIdle()
            assertEquals(0, gateway.opens)
            assertEquals(R.string.share_audio_unsupported, vm.state.value.error?.res)
            assertEquals("pasted", vm.state.value.caseText)
            assertNull(vm.state.value.draftAudio)
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun aNewSessionDropsThePreviousDraft() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val file = File.createTempFile("note", ".m4a").apply { writeBytes(byteArrayOf(1, 2)) }
            val vm = FamilyViewModel("fam-1", idleFamilies(), RecordingGateway())
            advanceUntilIdle()
            vm.bindSession("parent-a")
            vm.applyShare("secret", DraftAudio(file, "v.m4a", "audio/mp4"), null, "t")
            vm.bindSession("parent-a")
            assertEquals(FamilyPage.NewCase, vm.state.value.page)
            vm.bindSession("parent-b")
            assertEquals(FamilyPage.Home, vm.state.value.page)
            assertNull(vm.state.value.draftAudio)
            assertFalse(file.exists())
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun aRestoredDraftIsKeptForTheSameSession() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val file = File.createTempFile("kept", ".m4a").apply { writeBytes(byteArrayOf(1, 2, 3)) }
            val handle = SavedStateHandle(
                mapOf(
                    FamilyViewModel.KEY_PAGE to FamilyPage.NewCase.name,
                    FamilyViewModel.KEY_CASE_TEXT to "kept",
                    FamilyViewModel.KEY_FROM_SHARE to true,
                    FamilyViewModel.KEY_AUDIO_PATH to file.absolutePath,
                    FamilyViewModel.KEY_AUDIO_NAME to "kept.m4a",
                    FamilyViewModel.KEY_AUDIO_TYPE to "audio/mp4",
                ),
            )
            val vm = FamilyViewModel("fam-1", idleFamilies(), RecordingGateway(), handle)
            advanceUntilIdle()
            assertEquals("kept", vm.state.value.caseText)
            assertEquals(file.absolutePath, vm.state.value.draftAudio?.file?.absolutePath)
            vm.bindSession("same")
            assertEquals(FamilyPage.NewCase, vm.state.value.page)
            assertTrue(file.exists())
            file.delete()
        } finally {
            Dispatchers.resetMain()
        }
    }
}

private class RecordingGateway : CaseGateway {
    var opens = 0
    var lastText: String? = null
    var lastAudio: CaseAudio? = null
    override suspend fun open(childMemberId: String, text: String, audio: CaseAudio?): ParentCase {
        opens += 1
        lastText = text
        lastAudio = audio
        return sampleCase()
    }
    override suspend fun case(caseId: String) = sampleCase()
}

private class EmptyFamilies : FamilySource {
    override suspend fun members(familyId: String): List<Member> = emptyList()
    override suspend fun recentCases(familyId: String): List<CaseSummary> = emptyList()
    override suspend fun addChild(familyId: String, displayName: String) = ChildInvite("c", displayName, "invited", "S", "2026-11-08T00:00:00+00:00")
    override suspend fun reissueInvite(familyId: String, memberId: String) = InviteReissued("c", "S", "2026-11-08T00:00:00+00:00")
    override suspend fun decideJoin(familyId: String, memberId: String, decision: ApiClient.Decision) = MemberDecision(memberId, "active", null)
    override suspend fun decidePhoneChange(familyId: String, memberId: String, decision: ApiClient.Decision) = PhoneChangeDecision(memberId, "kept")
    override suspend fun addCallOnly(familyId: String, memberId: String, phoneE164: String) = LinkSent("link_sent", "0000")
}

private fun idleFamilies() = EmptyFamilies()
