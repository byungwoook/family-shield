package com.familyshield.app.ui.caseflow

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.familyshield.app.data.CaseSource
import com.familyshield.app.data.api.ApiException
import com.familyshield.app.data.api.ParentCase
import com.familyshield.app.domain.CaseColor
import com.familyshield.app.ui.common.ErrorMessages
import com.familyshield.app.ui.common.UiText
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlin.coroutines.coroutineContext
import kotlin.time.Duration
import kotlin.time.Duration.Companion.seconds

data class CaseUiState(
    val loading: Boolean = true,
    val case: ParentCase? = null,
    val error: UiText? = null,
)

/**
 * Polls `GET /v1/cases/{id}` about every 3 seconds while the screen is visible
 * and the colour is still open. Stops when the case is decided, when the
 * screen is not visible, and on 401 (the session layer signs out).
 */
class CaseViewModel(
    private val cases: CaseSource,
    private val caseId: String,
    initial: ParentCase? = null,
    private val pollEvery: Duration = 3.seconds,
) : ViewModel() {

    private val _state = MutableStateFlow(
        CaseUiState(loading = initial == null, case = initial),
    )
    val state: StateFlow<CaseUiState> = _state.asStateFlow()

    private var poll: Job? = null

    fun setVisible(visible: Boolean) {
        poll?.cancel()
        poll = null
        if (!visible) return
        poll = viewModelScope.launch { pollWhileOpen() }
    }

    private suspend fun pollWhileOpen() {
        while (coroutineContext.isActive) {
            val existing = _state.value.case
            if (existing != null && existing.isDecided()) {
                _state.value = _state.value.copy(loading = false)
                return
            }
            try {
                val fresh = cases.case(caseId)
                _state.value = CaseUiState(loading = false, case = fresh, error = null)
                if (fresh.isDecided()) return
            } catch (e: ApiException) {
                if (e is ApiException.Http && e.status == 401) return
                _state.value = _state.value.copy(loading = false, error = ErrorMessages.of(e))
            }
            delay(pollEvery)
        }
    }

    override fun onCleared() {
        poll?.cancel()
    }
}

internal fun ParentCase.isDecided(): Boolean = CaseColor.of(color, decidedAt).isDecided
