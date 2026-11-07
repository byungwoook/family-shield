package com.familyshield.app.share

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.OpenableColumns
import com.familyshield.app.domain.SharePlan
import com.familyshield.app.domain.ShareProblem
import com.familyshield.app.domain.ShareRequest
import com.familyshield.app.domain.VoiceNotes
import com.familyshield.app.domain.planShare
import java.io.File
import java.util.UUID

/** A voice note copied into app storage. Nothing has been uploaded. */
data class StoredAudio(
    val file: File,
    val displayName: String,
    val contentType: String,
    val sizeBytes: Long,
)

sealed class ShareOutcome {
    data object Ignore : ShareOutcome()
    data class Draft(val text: String, val audio: StoredAudio?, val problem: ShareProblem?) : ShareOutcome()
}

/**
 * Reads one `ACTION_SEND` and, for a voice note, copies it into [draftsDir].
 * The copy is the draft. `POST /v1/cases` happens later, when the parent taps Verify.
 * Only `content:` and `file:` streams are read. A link is not downloaded.
 */
class ShareIntake(
    context: Context,
    private val draftsDir: File = File(context.applicationContext.cacheDir, "share-drafts"),
    private val maxBytes: Long = VoiceNotes.MAX_BYTES,
) {
    fun receive(context: Context, intent: Intent): ShareOutcome {
        val uri = streamUri(intent)?.takeIf { it.scheme.equals("content", true) || it.scheme.equals("file", true) }
        val plan = planShare(
            ShareRequest(
                action = intent.action,
                mime = intent.type,
                text = sharedText(intent),
                hasStream = uri != null,
                displayName = uri?.let { displayName(context, it) },
                declaredSize = uri?.let { declaredSize(context, it) },
            ),
            maxBytes,
        )
        if (plan is SharePlan.Ignore) return ShareOutcome.Ignore
        val draft = plan as SharePlan.Draft
        val wanted = draft.audio
        if (wanted == null) {
            // A text share replaces a previous voice note. A rejected audio share
            // does not delete the previous file until the draft screen takes over.
            if (draft.problem == null) wipe()
            return ShareOutcome.Draft(draft.text, audio = null, problem = draft.problem)
        }
        val dest = File(draftsDir, "voice-${UUID.randomUUID()}.${VoiceNotes.suffix(wanted.contentType)}")
        val stream = try {
            context.contentResolver.openInputStream(uri ?: return ShareOutcome.Draft(draft.text, null, ShareProblem.UNREADABLE))
        } catch (_: Exception) {
            null
        }
        if (stream == null) {
            return ShareOutcome.Draft(draft.text, audio = null, problem = ShareProblem.UNREADABLE)
        }
        val copied = stream.use { VoiceNotes.copyCapped(it, dest, maxBytes) }
        return when (copied) {
            is VoiceNotes.Copy.Ok -> {
                deleteExcept(dest)
                ShareOutcome.Draft(
                    text = draft.text,
                    audio = StoredAudio(
                        file = dest,
                        displayName = VoiceNotes.displayLabel(wanted.displayName, wanted.contentType),
                        contentType = wanted.contentType,
                        sizeBytes = copied.bytes,
                    ),
                    problem = null,
                )
            }
            VoiceNotes.Copy.Empty -> ShareOutcome.Draft(draft.text, null, ShareProblem.EMPTY)
            VoiceNotes.Copy.TooLarge -> ShareOutcome.Draft(draft.text, null, ShareProblem.TOO_LARGE)
            VoiceNotes.Copy.Unreadable -> ShareOutcome.Draft(draft.text, null, ShareProblem.UNREADABLE)
        }
    }

    fun isOwned(file: File): Boolean {
        val root = draftsDir.absoluteFile
        val parent = file.absoluteFile.parentFile ?: return false
        return parent.path == root.path
    }

    fun wipe() {
        draftsDir.listFiles()?.forEach { if (it.isFile) it.delete() }
    }

    private fun deleteExcept(keep: File) {
        draftsDir.listFiles()?.forEach { file ->
            if (file.isFile && file.absolutePath != keep.absolutePath) file.delete()
        }
    }

    private fun displayName(context: Context, uri: Uri): String? {
        val queried = queryString(context, uri, OpenableColumns.DISPLAY_NAME)
        if (!queried.isNullOrBlank()) return queried
        return uri.lastPathSegment
    }

    private fun declaredSize(context: Context, uri: Uri): Long? {
        return try {
            context.contentResolver.query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)?.use { cursor ->
                if (!cursor.moveToFirst()) return null
                val index = cursor.getColumnIndex(OpenableColumns.SIZE)
                if (index < 0 || cursor.isNull(index)) null else cursor.getLong(index)
            }
        } catch (_: Exception) {
            null
        }
    }

    private fun queryString(context: Context, uri: Uri, column: String): String? {
        return try {
            context.contentResolver.query(uri, arrayOf(column), null, null, null)?.use { cursor ->
                if (!cursor.moveToFirst()) return null
                val index = cursor.getColumnIndex(column)
                if (index < 0 || cursor.isNull(index)) null else cursor.getString(index)
            }
        } catch (_: Exception) {
            null
        }
    }

    private fun sharedText(intent: Intent): String? {
        val extra = intent.getCharSequenceExtra(Intent.EXTRA_TEXT)?.toString()
        if (!extra.isNullOrEmpty()) return extra
        val clip = intent.clipData ?: return extra
        if (clip.itemCount < 1) return extra
        return clip.getItemAt(0).text?.toString() ?: extra
    }

    private fun streamUri(intent: Intent): Uri? {
        val extra: Uri? = if (Build.VERSION.SDK_INT >= 33) {
            intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent.getParcelableExtra(Intent.EXTRA_STREAM)
        }
        if (extra != null) return extra
        val clip = intent.clipData ?: return null
        if (clip.itemCount < 1) return null
        return clip.getItemAt(0).uri
    }
}
