package com.familyshield.app.share

import android.content.Intent
import android.net.Uri
import androidx.test.core.app.ApplicationProvider
import com.familyshield.app.domain.ShareProblem
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import java.io.ByteArrayInputStream
import java.io.File

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])
class ShareIntakeTest {
    private val context = ApplicationProvider.getApplicationContext<android.content.Context>()

    @Test
    fun textShareIsADraftAndDoesNotCreateAFile() {
        val dir = tempDir()
        val intake = ShareIntake(context, dir, maxBytes = 8)
        val outcome = intake.receive(context, Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, "send money")
        })
        val draft = outcome as ShareOutcome.Draft
        assertEquals("send money", draft.text)
        assertNull(draft.audio)
        assertNull(draft.problem)
        assertTrue(dir.listFiles().isNullOrEmpty())
    }

    @Test
    fun audioShareIsCopiedAndNotLeftWhenItExceedsTheLimit() {
        val dir = tempDir()
        val intake = ShareIntake(context, dir, maxBytes = 4)
        val uri = Uri.parse("content://share/voice.m4a")
        shadowOf(context.contentResolver).registerInputStream(uri, ByteArrayInputStream(byteArrayOf(1, 2, 3, 4)))
        val ok = intake.receive(context, audioIntent(uri, "audio/mp4")) as ShareOutcome.Draft
        assertEquals("audio/mp4", ok.audio?.contentType)
        assertEquals("voice.m4a", ok.audio?.displayName)
        assertEquals(4L, ok.audio?.sizeBytes)
        assertEquals(byteArrayOf(1, 2, 3, 4).toList(), ok.audio?.file?.readBytes()?.toList())
        assertNull(ok.problem)

        val big = Uri.parse("content://share/big.m4a")
        shadowOf(context.contentResolver).registerInputStream(big, ByteArrayInputStream(byteArrayOf(1, 2, 3, 4, 5)))
        val rejected = intake.receive(context, audioIntent(big, "audio/mp4")) as ShareOutcome.Draft
        assertEquals(ShareProblem.TOO_LARGE, rejected.problem)
        assertNull(rejected.audio)
        assertEquals(listOf(ok.audio!!.file.name), dir.list()?.toList())
    }

    @Test
    fun opusAndAmrAndGenericTypesAreStoredAsAudio() {
        val dir = tempDir()
        val intake = ShareIntake(context, dir, maxBytes = 16)
        assertEquals("audio/opus", copied(intake, "content://share/note.opus", "audio/ogg; codecs=opus").contentType)
        assertEquals("audio/amr", copied(intake, "content://share/note.amr", "audio/amr").contentType)
        assertEquals("audio/aac", copied(intake, "content://share/note.aac", "audio/aac").contentType)
        assertEquals(
            "audio/mp4",
            copied(intake, "content://share/note.m4a", "application/octet-stream").contentType,
        )
        assertEquals("audio/ogg", copied(intake, "content://share/note.ogg", "application/ogg").contentType)
    }

    @Test
    fun emptyAudioIsRejectedAndNoFileRemains() {
        val dir = tempDir()
        val intake = ShareIntake(context, dir, maxBytes = 8)
        val uri = Uri.parse("content://share/empty.m4a")
        shadowOf(context.contentResolver).registerInputStream(uri, ByteArrayInputStream(byteArrayOf()))
        val outcome = intake.receive(context, audioIntent(uri, "audio/mp4")) as ShareOutcome.Draft
        assertEquals(ShareProblem.EMPTY, outcome.problem)
        assertTrue(dir.listFiles().isNullOrEmpty())
    }

    @Test
    fun theSameIntentIsHandledOnce() {
        val inbox = ShareInbox(context)
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, "hello")
        }
        inbox.ingest(context, intent)
        inbox.ingest(context, intent)
        assertEquals("hello", inbox.pending.value?.text)
        inbox.ingest(context, Intent(Intent.ACTION_MAIN))
        assertEquals("hello", inbox.pending.value?.text)
    }

    private fun copied(intake: ShareIntake, rawUri: String, mime: String): StoredAudio {
        val uri = Uri.parse(rawUri)
        shadowOf(context.contentResolver).registerInputStream(uri, ByteArrayInputStream(byteArrayOf(9, 8, 7)))
        val draft = intake.receive(context, audioIntent(uri, mime)) as ShareOutcome.Draft
        return draft.audio ?: error("expected audio for $mime")
    }

    private fun audioIntent(uri: Uri, mime: String) = Intent(Intent.ACTION_SEND).apply {
        type = mime
        putExtra(Intent.EXTRA_STREAM, uri)
        putExtra(Intent.EXTRA_TEXT, "caption")
    }

    private fun tempDir(): File = File.createTempFile("drafts", "").apply { delete(); mkdirs() }
}
