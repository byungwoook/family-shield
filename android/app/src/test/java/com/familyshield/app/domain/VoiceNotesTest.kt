package com.familyshield.app.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.File
import java.io.IOException
import java.io.InputStream

class VoiceNotesTest {
    @Test
    fun limitIsTenMegabytes() {
        assertEquals(10_485_760L, VoiceNotes.MAX_BYTES)
    }

    @Test
    fun messengerFormatsBecomeAudioTypes() {
        val cases = listOf(
            Triple("audio/mp4", "voice.m4a", "audio/mp4"),
            Triple("audio/x-m4a", "voice.m4a", "audio/mp4"),
            Triple("audio/m4a", "voice.m4a", "audio/mp4"),
            Triple("audio/aac", "voice.aac", "audio/aac"),
            Triple("audio/x-aac", "voice.aac", "audio/aac"),
            Triple("audio/mp4a-latm", "voice.aac", "audio/aac"),
            Triple("audio/ogg", "voice.ogg", "audio/ogg"),
            Triple("audio/ogg; codecs=opus", "voice.ogg", "audio/ogg"),
            Triple("audio/ogg; codecs=opus", "voice.opus", "audio/opus"),
            Triple("audio/opus", "voice.opus", "audio/opus"),
            Triple("application/ogg", "voice.ogg", "audio/ogg"),
            Triple("application/ogg", "voice.opus", "audio/opus"),
            Triple("audio/amr", "voice.amr", "audio/amr"),
            Triple("audio/amr-wb", "voice.awb", "audio/amr"),
            Triple("audio/3gpp", "voice.3gp", "audio/3gpp"),
            Triple("application/octet-stream", "voice.m4a", "audio/mp4"),
            Triple("application/octet-stream", "voice.aac", "audio/aac"),
            Triple("application/octet-stream", "voice.ogg", "audio/ogg"),
            Triple("application/octet-stream", "voice.opus", "audio/opus"),
            Triple("application/octet-stream", "voice.amr", "audio/amr"),
            Triple("application/octet-stream", "memo.caf", "audio/x-caf"),
            Triple("audio/mpeg", "a.mp3", "audio/mpeg"),
            Triple("audio/wav", "a.wav", "audio/wav"),
            Triple("audio/webm", "a.webm", "audio/webm"),
            Triple("audio/x-caf", "memo.caf", "audio/x-caf"),
        )
        cases.forEach { (mime, name, expected) ->
            assertEquals("$mime $name", expected, VoiceNotes.contentType(mime, name))
        }
        assertEquals("audio/mp4", VoiceNotes.contentType(null, "voice.m4a"))
        assertNull(VoiceNotes.contentType(null, "clip.mp4"))
        assertNull(VoiceNotes.contentType("video/mp4", "clip.mp4"))
        assertNull(VoiceNotes.contentType("video/mp4", "voice.m4a"))
        assertNull(VoiceNotes.contentType("application/octet-stream", "clip.mp4"))
        assertNull(VoiceNotes.contentType("application/octet-stream", "voice.3gp"))
        assertNull(VoiceNotes.contentType("image/jpeg", "a.jpg"))
        assertNull(VoiceNotes.contentType("text/plain", "a.txt"))
    }

    @Test
    fun uploadNameDropsPathsAndUnsafeCharacters() {
        assertEquals("voice.m4a", VoiceNotes.uploadName("voice.m4a", "audio/mp4"))
        assertEquals("passwd.m4a", VoiceNotes.uploadName("../../etc/passwd.m4a", "audio/mp4"))
        assertEquals("voice-note.m4a", VoiceNotes.uploadName("엄마 음성.m4a", "audio/mp4"))
        assertEquals("voice-note.ogg", VoiceNotes.uploadName(null, "audio/ogg"))
        assertEquals("ab.m4a", VoiceNotes.uploadName("a\"b\n.m4a", "audio/mp4"))
        assertEquals("엄마 음성.m4a", VoiceNotes.displayLabel("folder/엄마 음성.m4a", "audio/mp4"))
    }

    @Test
    fun copyStopsAtTheLimitAndDeletesThePartialFile() {
        val dir = File.createTempFile("notes", "").apply { delete(); mkdirs() }
        val ok = File(dir, "ok.bin")
        val copied = VoiceNotes.copyCapped(ByteArrayInputStream(byteArrayOf(1, 2, 3, 4)), ok, limit = 4)
        assertTrue(copied is VoiceNotes.Copy.Ok)
        assertEquals(4, ok.length())

        val big = File(dir, "big.bin")
        val tooBig = VoiceNotes.copyCapped(ByteArrayInputStream(byteArrayOf(1, 2, 3, 4, 5)), big, limit = 4)
        assertEquals(VoiceNotes.Copy.TooLarge, tooBig)
        assertFalse(big.exists())

        val empty = File(dir, "empty.bin")
        assertEquals(VoiceNotes.Copy.Empty, VoiceNotes.copyCapped(ByteArrayInputStream(byteArrayOf()), empty, limit = 4))
        assertFalse(empty.exists())

        val broken = object : InputStream() {
            override fun read(): Int = throw IOException("disk")
        }
        val bad = File(dir, "bad.bin")
        assertEquals(VoiceNotes.Copy.Unreadable, VoiceNotes.copyCapped(broken, bad, limit = 4))
        assertFalse(bad.exists())
        dir.deleteRecursively()
    }

    @Test
    fun exactlyTenMegabytesIsAllowedAndOneMoreByteIsNot() {
        val atLimit = planShare(
            ShareRequest(ACTION, "audio/mp4", "", hasStream = true, displayName = "v.m4a", declaredSize = VoiceNotes.MAX_BYTES),
        )
        assertTrue(atLimit is SharePlan.Draft && atLimit.audio != null && atLimit.problem == null)
        val over = planShare(
            ShareRequest(ACTION, "audio/mp4", "caption", hasStream = true, displayName = "v.m4a", declaredSize = VoiceNotes.MAX_BYTES + 1),
        )
        assertTrue(over is SharePlan.Draft)
        assertNull((over as SharePlan.Draft).audio)
        assertEquals(ShareProblem.TOO_LARGE, over.problem)
        assertEquals("caption", over.text)
    }

    @Test
    fun plainTextIsADraftWithNoAudio() {
        val plan = planShare(ShareRequest(ACTION, "text/plain", "용돈 보내줘", hasStream = false, displayName = null, declaredSize = null))
        assertTrue(plan is SharePlan.Draft)
        val draft = plan as SharePlan.Draft
        assertEquals("용돈 보내줘", draft.text)
        assertNull(draft.audio)
        assertNull(draft.problem)
    }

    @Test
    fun textIsCappedAt8000Characters() {
        val plan = planShare(ShareRequest(ACTION, "text/plain", "가".repeat(9000), false, null, null))
        assertEquals(8000, (plan as SharePlan.Draft).text.length)
    }

    @Test
    fun emptyDeclaredAudioIsRejectedBeforeACopy() {
        val plan = planShare(ShareRequest(ACTION, "audio/amr", "", true, "n.amr", 0))
        assertEquals(ShareProblem.EMPTY, (plan as SharePlan.Draft).problem)
        assertNull(plan.audio)
    }

    @Test
    fun aVideoIsNotAVoiceNote() {
        val plan = planShare(ShareRequest(ACTION, "video/mp4", "", true, "clip.mp4", 100))
        assertEquals(ShareProblem.UNSUPPORTED, (plan as SharePlan.Draft).problem)
    }

    @Test
    fun launcherIntentIsIgnored() {
        assertTrue(planShare(ShareRequest("android.intent.action.MAIN", null, null, false, null, null)) is SharePlan.Ignore)
    }

    private companion object {
        const val ACTION = "android.intent.action.SEND"
    }
}
