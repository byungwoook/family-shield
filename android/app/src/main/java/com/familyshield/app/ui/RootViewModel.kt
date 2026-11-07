package com.familyshield.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.familyshield.app.data.AuthRepository
import com.familyshield.app.data.CaseRepository
import com.familyshield.app.data.api.ApiException
import com.familyshield.app.data.api.FamilyCreated
import com.familyshield.app.data.api.Me
import com.familyshield.app.data.session.SessionManager
import com.familyshield.app.ui.common.ErrorMessages
import com.familyshield.app.ui.common.UiText
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Which top-level screen the app shows. */
sealed interface RootState {
    data object Loading : RootState
    data object SignedOut : RootState
    data object NeedsFamily : RootState
    data class Parent(val familyId: String, val familyName: String) : RootState
    data class Child(val familyName: String) : RootState
    data object MembershipPending : RootState
    data class Failed(val message: UiText) : RootState
}

/**
 * Session to screen. Signed in: `GET /v1/me` decides between creating a
 * family, the parent screens, and the child placeholder (the child path is
 * milestone 14). A sign-out anywhere, including a 401, lands on sign-in.
 */
class RootViewModel(
    private val session: SessionManager,
    private val auth: AuthRepository,
    private val cases: CaseRepository,
    private val io: CoroutineDispatcher = Dispatchers.IO,
) : ViewModel() {

    private val _state = MutableStateFlow<RootState>(RootState.Loading)
    val state: StateFlow<RootState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            withContext(io) { session.load() }
            session.token.collectLatest { token ->
                if (token == null) {
                    cases.clear()
                    _state.value = RootState.SignedOut
                } else {
                    resolve()
                }
            }
        }
    }

    private suspend fun resolve() {
        _state.value = RootState.Loading
        try {
            _state.value = route(auth.me())
        } catch (e: ApiException) {
            // A 401 already signed the session out; the token collector shows sign-in.
            if (e is ApiException.Http && e.status == 401) return
            _state.value = RootState.Failed(ErrorMessages.of(e))
        }
    }

    fun retry() {
        if (session.currentToken() == null) return
        viewModelScope.launch { resolve() }
    }

    fun familyCreated(family: FamilyCreated) {
        _state.value = RootState.Parent(family.id, family.name)
    }

    fun signOut() = auth.signOut()

    companion object {
        /** The contract's rule (§5 Me): a parent with an active parent membership uses that family. */
        fun route(me: Me): RootState {
            if (me.memberships.isEmpty()) return RootState.NeedsFamily
            me.memberships.firstOrNull { it.role == "parent" && it.status == "active" }
                ?.let { return RootState.Parent(it.familyId, it.familyName) }
            me.memberships.firstOrNull { it.role == "child" }
                ?.let { return RootState.Child(it.familyName) }
            return RootState.MembershipPending
        }
    }
}
