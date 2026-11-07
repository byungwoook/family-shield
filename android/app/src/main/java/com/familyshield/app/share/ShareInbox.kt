package com.familyshield.app.share

import android.content.Context
import android.content.Intent
import com.familyshield.app.domain.ShareProblem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.io.File

/** One incoming share waiting for the parent home. The file is local until Verify. */
data class PendingShare(
    val token: String,
    val text: String,
    val audio: StoredAudio?,
    val problem: ShareProblem?,
)

/**
 * Holds the latest `ACTION_SEND` for the activity. The same Intent instance is
 * handled once, so a rotation does not copy the voice note again or reset the
 * draft the parent is editing. A new share (a new Intent) replaces it.
 */
class ShareInbox(context: Context) {
    private val intake = ShareIntake(context.applicationContext)
    private val _pending = MutableStateFlow<PendingShare?>(null)
    val pending: StateFlow<PendingShare?> = _pending.asStateFlow()
    private var handledIdentity: Int? = null

    fun ingest(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_SEND) return
        val identity = System.identityHashCode(intent)
        if (identity == handledIdentity) return
        handledIdentity = identity
        val outcome = intake.receive(context, intent)
        if (outcome !is ShareOutcome.Draft) return
        _pending.value = PendingShare(
            token = identity.toString(),
            text = outcome.text,
            audio = outcome.audio,
            problem = outcome.problem,
        )
    }

    /** The parent screen now owns the draft. The file stays until Verify or discard. */
    fun consume(token: String) {
        if (_pending.value?.token == token) _pending.value = null
    }

    /** Drop a share that this account cannot verify, and delete its file. */
    fun discardPending() {
        _pending.value = null
        intake.wipe()
    }

    /** Deletes [file] only when it is one of our draft copies. */
    fun delete(file: File) {
        if (intake.isOwned(file) && file.isFile) file.delete()
    }
}
