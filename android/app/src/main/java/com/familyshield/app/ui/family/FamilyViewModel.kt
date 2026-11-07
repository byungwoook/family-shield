package com.familyshield.app.ui.family

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.familyshield.app.R
import com.familyshield.app.data.CaseGateway
import com.familyshield.app.data.FamilySource
import com.familyshield.app.data.api.ApiClient
import com.familyshield.app.data.api.ApiException
import com.familyshield.app.data.api.CaseAudio
import com.familyshield.app.data.api.CaseSummary
import com.familyshield.app.data.api.Member
import com.familyshield.app.data.api.ParentCase
import com.familyshield.app.domain.MemberRules
import com.familyshield.app.domain.PhoneInput
import com.familyshield.app.domain.ShareProblem
import com.familyshield.app.domain.VoiceNotes
import com.familyshield.app.ui.common.ErrorMessages
import com.familyshield.app.ui.common.UiText
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.io.File

enum class FamilyPage { Home, NewCase }

data class ShownInvite(
    val name: String,
    val secret: String,
    val expiresAt: String,
)

/** A voice note copied into app storage. It is not uploaded until Verify. */
data class DraftAudio(
    val file: File,
    val displayName: String,
    val contentType: String,
)

data class FamilyUiState(
    val loading: Boolean = true,
    val members: List<Member> = emptyList(),
    val recent: List<CaseSummary> = emptyList(),
    val error: UiText? = null,
    val notice: UiText? = null,
    val invite: ShownInvite? = null,
    val page: FamilyPage = FamilyPage.Home,
    val busy: Boolean = false,
    val addName: String = "",
    val addPhone: String = "",
    val addByPhone: Boolean = false,
    val showAdd: Boolean = false,
    val callOnlyMemberId: String? = null,
    val caseChildId: String? = null,
    val caseText: String = "",
    val draftAudio: DraftAudio? = null,
    val fromShare: Boolean = false,
)

/**
 * The parent home: roster, invite secret (shown once), confirm / reject,
 * number-change confirm, call-only add, and opening a case.
 */
class FamilyViewModel(
    private val familyId: String,
    private val families: FamilySource,
    private val cases: CaseGateway,
    private val savedState: SavedStateHandle = SavedStateHandle(),
    private val deleteDraft: (File) -> Unit = { it.delete() },
) : ViewModel() {

    private var appliedShare: String? = null
    private var boundToken: String? = null

    private val _state = MutableStateFlow(
        FamilyUiState(
            invite = savedState.get<String>(KEY_SECRET)?.let { secret ->
                ShownInvite(
                    name = savedState.get<String>(KEY_NAME).orEmpty(),
                    secret = secret,
                    expiresAt = savedState.get<String>(KEY_EXPIRES).orEmpty(),
                )
            },
            page = savedState.get<String>(KEY_PAGE)?.let { runCatching { FamilyPage.valueOf(it) }.getOrNull() }
                ?: FamilyPage.Home,
            caseText = savedState.get<String>(KEY_CASE_TEXT).orEmpty(),
            caseChildId = savedState.get<String>(KEY_CASE_CHILD),
            fromShare = savedState.get<Boolean>(KEY_FROM_SHARE) == true,
            draftAudio = restoredAudio(savedState),
        ),
    )
    val state: StateFlow<FamilyUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch { _state.collect { persistCase(it) } }
        refresh()
    }

    /**
     * A new session token means a different sign-in. Drop a draft left by the
     * previous one. The first bind keeps a draft restored after process death.
     */
    fun bindSession(token: String?) {
        if (token == null) return
        val previous = boundToken
        if (previous == null) {
            boundToken = token
            return
        }
        if (previous != token) {
            boundToken = token
            discardDraft()
        }
    }

    /**
     * Opens the new-case screen with the shared text and voice note. Does not
     * call the server. The same [token] twice does not wipe edits.
     */
    fun applyShare(text: String, audio: DraftAudio?, problem: ShareProblem?, token: String) {
        if (token == appliedShare && _state.value.page == FamilyPage.NewCase) return
        appliedShare = token
        val previous = _state.value.draftAudio?.file
        if (previous != null && previous != audio?.file) deleteDraft(previous)
        val ready = _state.value.members.filter { MemberRules.canVerify(it) }
        _state.update {
            it.copy(
                page = FamilyPage.NewCase,
                caseText = text.take(TEXT_LIMIT),
                caseChildId = it.caseChildId ?: ready.singleOrNull()?.id,
                draftAudio = audio,
                fromShare = true,
                error = problem?.let { problemText(it) },
            )
        }
    }

    fun removeDraftAudio() {
        _state.value.draftAudio?.let { deleteDraft(it.file) }
        _state.update { it.copy(draftAudio = null) }
    }

    /** Leaves the draft and deletes the copied voice note. Nothing was uploaded. */
    fun discardDraft() {
        _state.value.draftAudio?.let { deleteDraft(it.file) }
        appliedShare = null
        _state.update {
            it.copy(page = FamilyPage.Home, caseText = "", draftAudio = null, fromShare = false, error = null)
        }
    }

    fun refresh(clearError: Boolean = true) {
        viewModelScope.launch {
            _state.update { it.copy(loading = it.members.isEmpty(), error = if (clearError) null else it.error) }
            try {
                val members = families.members(familyId)
                val recent = families.recentCases(familyId)
                val onlyReady = members.filter { MemberRules.canVerify(it) }.singleOrNull()?.id
                _state.update {
                    it.copy(
                        loading = false,
                        members = members,
                        recent = recent,
                        error = if (clearError && !(it.fromShare && it.error != null)) null else it.error,
                        caseChildId = if (it.page == FamilyPage.NewCase && it.caseChildId == null) onlyReady else it.caseChildId,
                    )
                }
            } catch (e: ApiException) {
                if (e is ApiException.Http && e.status == 401) return@launch
                _state.update { it.copy(loading = false, error = ErrorMessages.of(e)) }
            }
        }
    }

    fun showAdd(show: Boolean) = _state.update {
        it.copy(showAdd = show, addName = if (show) it.addName else "", addPhone = "", addByPhone = false, error = null)
    }

    fun setAddName(value: String) = _state.update { it.copy(addName = value.take(NAME_LIMIT), error = null) }
    fun setAddPhone(value: String) = _state.update { it.copy(addPhone = value.take(PHONE_LIMIT), error = null) }
    fun setAddByPhone(value: Boolean) = _state.update { it.copy(addByPhone = value, error = null) }

    fun addChild() {
        val name = _state.value.addName.trim()
        if (name.isEmpty()) {
            _state.update { it.copy(error = UiText(R.string.error_name_required)) }
            return
        }
        val phone = if (_state.value.addByPhone) parsePhoneOrNull() ?: return else null
        if (_state.value.busy) return
        viewModelScope.launch {
            _state.update { it.copy(busy = true, error = null) }
            try {
                val invite = families.addChild(familyId, name)
                if (phone == null) {
                    rememberInvite(ShownInvite(invite.displayName, invite.inviteSecret, invite.inviteExpiresAt))
                    _state.update { it.copy(busy = false, showAdd = false, addName = "", addPhone = "") }
                } else {
                    try {
                        val sent = families.addCallOnly(familyId, invite.id, phone)
                        clearInvite()
                        _state.update {
                            it.copy(
                                busy = false,
                                showAdd = false,
                                addName = "",
                                addPhone = "",
                                notice = UiText.of(R.string.notice_link_sent, name, sent.phoneLast4.orEmpty()),
                            )
                        }
                    } catch (e: ApiException) {
                        // The secret was returned once. Call-only did not burn it, so show it.
                        rememberInvite(ShownInvite(invite.displayName, invite.inviteSecret, invite.inviteExpiresAt))
                        _state.update { it.copy(busy = false, showAdd = false, error = ErrorMessages.of(e)) }
                        refresh(clearError = false)
                        return@launch
                    }
                }
                refresh()
            } catch (e: ApiException) {
                _state.update { it.copy(busy = false, error = ErrorMessages.of(e)) }
            }
        }
    }

    fun showCallOnly(memberId: String?) = _state.update { it.copy(callOnlyMemberId = memberId, addPhone = "", error = null) }

    fun submitCallOnly() {
        val memberId = _state.value.callOnlyMemberId ?: return
        val phone = parsePhoneOrNull() ?: return
        val name = _state.value.members.firstOrNull { it.id == memberId }?.displayName.orEmpty()
        launchAction {
            val sent = families.addCallOnly(familyId, memberId, phone)
            _state.update {
                it.copy(
                    callOnlyMemberId = null,
                    addPhone = "",
                    notice = UiText.of(R.string.notice_link_sent, name, sent.phoneLast4.orEmpty()),
                )
            }
        }
    }

    fun reissue(memberId: String) {
        val name = _state.value.members.firstOrNull { it.id == memberId }?.displayName.orEmpty()
        launchAction {
            val invite = families.reissueInvite(familyId, memberId)
            rememberInvite(ShownInvite(name, invite.inviteSecret, invite.inviteExpiresAt))
        }
    }

    fun dismissInvite() {
        clearInvite()
        _state.update { it.copy(invite = null) }
    }

    fun confirmJoin(memberId: String) = decideJoin(memberId, ApiClient.Decision.CONFIRM)
    fun rejectJoin(memberId: String) = decideJoin(memberId, ApiClient.Decision.REJECT)

    private fun decideJoin(memberId: String, decision: ApiClient.Decision) {
        val name = _state.value.members.firstOrNull { it.id == memberId }?.displayName.orEmpty()
        launchAction {
            families.decideJoin(familyId, memberId, decision)
            val notice = if (decision == ApiClient.Decision.CONFIRM) {
                UiText.of(R.string.notice_child_confirmed, name)
            } else {
                UiText.of(R.string.notice_child_rejected, name)
            }
            _state.update { it.copy(notice = notice) }
        }
    }

    fun confirmPhone(memberId: String) = decidePhone(memberId, ApiClient.Decision.CONFIRM)
    fun rejectPhone(memberId: String) = decidePhone(memberId, ApiClient.Decision.REJECT)

    private fun decidePhone(memberId: String, decision: ApiClient.Decision) {
        val name = _state.value.members.firstOrNull { it.id == memberId }?.displayName.orEmpty()
        launchAction {
            val result = families.decidePhoneChange(familyId, memberId, decision)
            val notice = when {
                decision == ApiClient.Decision.REJECT -> UiText.of(R.string.notice_number_kept, name)
                (result.cancelledCases ?: 0) > 0 ->
                    UiText.of(R.string.notice_number_changed_cancelled, name, result.phoneLast4.orEmpty())
                else -> UiText.of(R.string.notice_number_changed, name, result.phoneLast4.orEmpty())
            }
            _state.update { it.copy(notice = notice) }
        }
    }

    fun dismissNotice() = _state.update { it.copy(notice = null) }

    fun openNewCase() {
        _state.value.draftAudio?.let { deleteDraft(it.file) }
        appliedShare = null
        val ready = _state.value.members.filter { MemberRules.canVerify(it) }
        _state.update {
            it.copy(
                page = FamilyPage.NewCase,
                caseChildId = ready.singleOrNull()?.id,
                caseText = "",
                draftAudio = null,
                fromShare = false,
                error = null,
            )
        }
    }

    fun closeNewCase() {
        _state.value.draftAudio?.let { deleteDraft(it.file) }
        appliedShare = null
        _state.update { it.copy(page = FamilyPage.Home, caseText = "", draftAudio = null, fromShare = false, error = null) }
    }
    fun selectChild(id: String) = _state.update { it.copy(caseChildId = id, error = null) }
    fun setCaseText(value: String) = _state.update { it.copy(caseText = value.take(TEXT_LIMIT), error = null) }

    fun verify(onOpened: (ParentCase) -> Unit) {
        val childId = _state.value.caseChildId
        if (childId == null) {
            _state.update { it.copy(error = UiText(R.string.new_case_no_children)) }
            return
        }
        val draft = _state.value.draftAudio
        val problem = draft?.let { audioProblem(it) }
        if (problem != null) {
            _state.update { it.copy(error = problemText(problem)) }
            return
        }
        if (_state.value.busy) return
        viewModelScope.launch {
            _state.update { it.copy(busy = true, error = null) }
            try {
                val audio = draft?.let {
                    CaseAudio(it.file, VoiceNotes.uploadName(it.displayName, it.contentType), it.contentType)
                }
                val opened = cases.open(childId, _state.value.caseText.trim(), audio)
                draft?.let { deleteDraft(it.file) }
                appliedShare = null
                _state.update {
                    it.copy(busy = false, page = FamilyPage.Home, caseText = "", draftAudio = null, fromShare = false)
                }
                onOpened(opened)
            } catch (e: ApiException) {
                _state.update { it.copy(busy = false, error = ErrorMessages.of(e)) }
            }
        }
    }

    private fun parsePhoneOrNull(): String? {
        return when (val parsed = PhoneInput.parse(_state.value.addPhone)) {
            is PhoneInput.Valid -> parsed.e164
            PhoneInput.Invalid -> {
                _state.update { it.copy(error = UiText(R.string.error_invalid_phone)) }
                null
            }
            PhoneInput.UnsupportedCountry -> {
                _state.update { it.copy(error = UiText(R.string.error_unsupported_country)) }
                null
            }
        }
    }

    private fun launchAction(block: suspend () -> Unit) {
        if (_state.value.busy) return
        viewModelScope.launch {
            _state.update { it.copy(busy = true, error = null) }
            try {
                block()
                _state.update { it.copy(busy = false) }
                refresh()
            } catch (e: ApiException) {
                _state.update { it.copy(busy = false, error = ErrorMessages.of(e)) }
            }
        }
    }

    private fun rememberInvite(invite: ShownInvite) {
        savedState[KEY_SECRET] = invite.secret
        savedState[KEY_NAME] = invite.name
        savedState[KEY_EXPIRES] = invite.expiresAt
        _state.update { it.copy(invite = invite) }
    }

    private fun clearInvite() {
        savedState.remove<String>(KEY_SECRET)
        savedState.remove<String>(KEY_NAME)
        savedState.remove<String>(KEY_EXPIRES)
    }

    private fun problemText(problem: ShareProblem): UiText = when (problem) {
        ShareProblem.TOO_LARGE -> UiText(R.string.share_audio_too_large)
        ShareProblem.EMPTY -> UiText(R.string.share_audio_empty)
        ShareProblem.UNSUPPORTED -> UiText(R.string.share_audio_unsupported)
        ShareProblem.UNREADABLE -> UiText(R.string.share_audio_unreadable)
    }

    private fun audioProblem(draft: DraftAudio): ShareProblem? {
        if (!draft.contentType.startsWith("audio/")) return ShareProblem.UNSUPPORTED
        if (!draft.file.isFile) return ShareProblem.UNREADABLE
        val length = draft.file.length()
        return when {
            length <= 0L -> ShareProblem.EMPTY
            length > VoiceNotes.MAX_BYTES -> ShareProblem.TOO_LARGE
            else -> null
        }
    }

    private fun persistCase(state: FamilyUiState) {
        savedState[KEY_PAGE] = state.page.name
        savedState[KEY_CASE_TEXT] = state.caseText
        if (state.caseChildId == null) savedState.remove<String>(KEY_CASE_CHILD) else savedState[KEY_CASE_CHILD] = state.caseChildId
        savedState[KEY_FROM_SHARE] = state.fromShare
        val audio = state.draftAudio
        if (audio == null) {
            savedState.remove<String>(KEY_AUDIO_PATH)
            savedState.remove<String>(KEY_AUDIO_NAME)
            savedState.remove<String>(KEY_AUDIO_TYPE)
        } else {
            savedState[KEY_AUDIO_PATH] = audio.file.absolutePath
            savedState[KEY_AUDIO_NAME] = audio.displayName
            savedState[KEY_AUDIO_TYPE] = audio.contentType
        }
    }

    companion object {
        const val NAME_LIMIT = 200
        const val PHONE_LIMIT = 32
        const val TEXT_LIMIT = 8000
        private const val KEY_SECRET = "invite_secret"
        private const val KEY_NAME = "invite_name"
        private const val KEY_EXPIRES = "invite_expires"
        internal const val KEY_PAGE = "case_page"
        internal const val KEY_CASE_TEXT = "case_text"
        internal const val KEY_CASE_CHILD = "case_child"
        internal const val KEY_FROM_SHARE = "case_from_share"
        internal const val KEY_AUDIO_PATH = "case_audio_path"
        internal const val KEY_AUDIO_NAME = "case_audio_name"
        internal const val KEY_AUDIO_TYPE = "case_audio_type"

        private fun restoredAudio(savedState: SavedStateHandle): DraftAudio? {
            val path = savedState.get<String>(KEY_AUDIO_PATH) ?: return null
            val type = savedState.get<String>(KEY_AUDIO_TYPE) ?: return null
            if (!type.startsWith("audio/")) return null
            val file = File(path)
            if (!file.isFile || file.length() <= 0L || file.length() > VoiceNotes.MAX_BYTES) return null
            return DraftAudio(file, savedState.get<String>(KEY_AUDIO_NAME) ?: file.name, type)
        }
    }
}
