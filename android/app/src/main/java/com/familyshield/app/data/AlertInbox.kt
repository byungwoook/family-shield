package com.familyshield.app.data

import android.content.Intent
import com.familyshield.app.domain.AlertPayload
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * The latest money-request push the activity received. Only `kind` and
 * `case_id` are read. A code extra on the same intent is ignored, and nothing
 * is written to disk.
 */
class AlertInbox {
    private val _generation = MutableStateFlow(0)
    val generation: StateFlow<Int> = _generation.asStateFlow()
    private var caseId: String? = null

    fun currentCaseId(): String? = caseId

    fun ingest(intent: Intent) {
        val data = buildMap {
            intent.getStringExtra(AlertPayload.EXTRA_KIND)?.let { put(AlertPayload.EXTRA_KIND, it) }
            intent.getStringExtra(AlertPayload.EXTRA_CASE_ID)?.let { put(AlertPayload.EXTRA_CASE_ID, it) }
        }
        val alert = AlertPayload.moneyRequest(data) ?: return
        caseId = alert.caseId
        _generation.value += 1
    }
}
