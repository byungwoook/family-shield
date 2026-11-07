package com.familyshield.app.domain

/** Why a share did not become an attached voice note. The text, if any, is still kept. */
enum class ShareProblem {
    TOO_LARGE,
    EMPTY,
    UNSUPPORTED,
    UNREADABLE,
}

data class PlannedAudio(val contentType: String, val displayName: String)

sealed class SharePlan {
    data object Ignore : SharePlan()
    data class Draft(val text: String, val audio: PlannedAudio?, val problem: ShareProblem?) : SharePlan()
}

/** The fields of an `ACTION_SEND` that decide the draft, with no Android types. */
data class ShareRequest(
    val action: String?,
    val mime: String?,
    val text: String?,
    val hasStream: Boolean,
    val displayName: String?,
    val declaredSize: Long?,
)

private const val ACTION_SEND = "android.intent.action.SEND"
private const val TEXT_LIMIT = 8000

/**
 * Decides what an `ACTION_SEND` becomes. `text/plain` is a text draft.
 * Audio is planned only when the type (or a known extension) is a voice note
 * and the reported size is within [maxBytes]. Copying the bytes is separate:
 * a missing or lying size is caught while the file is copied.
 * Sharing never uploads. The parent still taps Verify.
 */
fun planShare(request: ShareRequest, maxBytes: Long = VoiceNotes.MAX_BYTES): SharePlan {
    if (request.action != ACTION_SEND) return SharePlan.Ignore
    val text = request.text.orEmpty().take(TEXT_LIMIT)
    val mime = VoiceNotes.baseType(request.mime)
    if (mime == "text/plain") {
        return SharePlan.Draft(text = text, audio = null, problem = null)
    }
    val namedAudio = request.hasStream && VoiceNotes.contentType(request.mime, request.displayName) != null
    val typedAudio = mime != null && (mime.startsWith("audio/") || mime == "application/ogg")
    if (!namedAudio && !typedAudio) {
        if (mime == null && text.isNotEmpty() && !request.hasStream) {
            return SharePlan.Draft(text = text, audio = null, problem = null)
        }
        return SharePlan.Draft(text = text, audio = null, problem = ShareProblem.UNSUPPORTED)
    }
    if (!request.hasStream) {
        return SharePlan.Draft(text = text, audio = null, problem = ShareProblem.UNSUPPORTED)
    }
    val contentType = VoiceNotes.contentType(request.mime, request.displayName)
        ?: return SharePlan.Draft(text = text, audio = null, problem = ShareProblem.UNSUPPORTED)
    val size = request.declaredSize
    if (size == 0L) {
        return SharePlan.Draft(text = text, audio = null, problem = ShareProblem.EMPTY)
    }
    if (size != null && size > maxBytes) {
        return SharePlan.Draft(text = text, audio = null, problem = ShareProblem.TOO_LARGE)
    }
    val name = request.displayName?.trim()?.takeIf { it.isNotEmpty() }
        ?: "voice-note.${VoiceNotes.suffix(contentType)}"
    return SharePlan.Draft(text = text, audio = PlannedAudio(contentType, name), problem = null)
}
