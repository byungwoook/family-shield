package com.familyshield.app.ui.child

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.familyshield.app.R
import com.familyshield.app.data.ChildProgress
import com.familyshield.app.data.ChildSource
import com.familyshield.app.data.api.ApiException
import com.familyshield.app.data.api.ChildCase
import com.familyshield.app.data.api.ErrorCodes
import com.familyshield.app.domain.ChildRules
import com.familyshield.app.domain.PhoneInput
import com.familyshield.app.ui.common.ErrorMessages
import com.familyshield.app.ui.common.UiText
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlin.coroutines.coroutineContext
import kotlin.time.Duration
import kotlin.time.Duration.Companion.seconds

data class ChildUiState(
    val step: ChildRules.Step,
    val status: String,
    val familyName: String,
    val phone: String = "",
    val phoneE164: String = "",
    val phoneLast4: String? = null,
    val otp: String = "",
    val code: String = "",
    val codeAgain: String = "",
    val busy: Boolean = false,
    val error: UiText? = null,
    val notice: UiText? = null,
    val caseId: String? = null,
    val case: ChildCase? = null,
    /** The question is on screen. "Not now" clears this and does not answer. */
    val prompt: Boolean = false,
    val pendingBiometric: BiometricPurpose? = null,
    /** The 6-digit code, in memory only, after a biometric check. Null when hidden. */
    val revealedCode: String? = null,
    val callFallback: Boolean = false,
    val resetOpen: Boolean = false,
    val resetUnlocked: Boolean = false,
)

/**
 * The child path: invite is a separate screen, then phone, SMS code, check
 * code, and the question. The one-time call code is fetched only after
 * biometrics and dropped when the child hides it or the call ends. It is
 * never written to [ChildProgress].
 */
class ChildViewModel(
    private val memberId: String,
    familyName: String,
    status: String,
    private val child: ChildSource,
    private val progress: ChildProgress,
    private val pollEvery: Duration = 3.seconds,
) : ViewModel() {

    private val _state = MutableStateFlow(
        ChildUiState(
            step = ChildRules.step(status, progress.isPhoneVerified(memberId), progress.isCheckCodeSet(memberId)),
            status = status,
            familyName = familyName,
        ),
    )
    val state: StateFlow<ChildUiState> = _state.asStateFlow()

    private var poll: Job? = null

    fun setPhone(value: String) = _state.update { it.copy(phone = value.take(32), error = null) }

    fun setOtp(value: String) = _state.update { it.copy(otp = ChildRules.digits(value, 6), error = null) }

    fun setCode(value: String) = _state.update { it.copy(code = ChildRules.digits(value, 4), error = null) }

    fun setCodeAgain(value: String) = _state.update { it.copy(codeAgain = ChildRules.digits(value, 4), error = null) }

    fun dismissNotice() = _state.update { it.copy(notice = null) }

    fun submitPhone() = sendOtp("sms")

    fun resendOtp() = sendOtp("sms")

    fun callWithOtp() = sendOtp("voice")

    private fun sendOtp(channel: String) {
        if (_state.value.busy) return
        val target = if (_state.value.step == ChildRules.Step.OTP && _state.value.phoneE164.isNotEmpty()) {
            _state.value.phoneE164
        } else {
            when (val parsed = PhoneInput.parse(_state.value.phone)) {
                is PhoneInput.Valid -> parsed.e164
                PhoneInput.Invalid -> {
                    _state.update { it.copy(error = UiText(R.string.error_invalid_phone)) }
                    return
                }
                PhoneInput.UnsupportedCountry -> {
                    _state.update { it.copy(error = UiText(R.string.error_unsupported_country)) }
                    return
                }
            }
        }
        _state.update { it.copy(busy = true, error = null, phoneE164 = target) }
        viewModelScope.launch {
            try {
                val started = child.startOtp(target, channel, biometricOk = false)
                _state.update {
                    it.copy(
                        busy = false,
                        step = ChildRules.Step.OTP,
                        phoneE164 = target,
                        phoneLast4 = started.phoneLast4,
                        otp = "",
                    )
                }
            } catch (e: ApiException) {
                if (e.isCode(ErrorCodes.PHONE_ALREADY_SET)) {
                    progress.markPhoneVerified(memberId)
                    _state.update {
                        it.copy(
                            busy = false,
                            phoneE164 = target,
                            step = landed(),
                            notice = UiText(R.string.child_phone_already),
                        )
                    }
                } else {
                    _state.update { it.copy(busy = false, error = otpFailure(e)) }
                }
            }
        }
    }

    fun submitOtp() {
        if (_state.value.busy) return
        val code = _state.value.otp
        val phone = _state.value.phoneE164
        if (!ChildRules.isOtp(code) || phone.isEmpty()) {
            _state.update { it.copy(error = UiText(R.string.error_otp_wrong)) }
            return
        }
        _state.update { it.copy(busy = true, error = null) }
        viewModelScope.launch {
            try {
                child.checkOtp(phone, code)
                progress.markPhoneVerified(memberId)
                _state.update { it.copy(busy = false, otp = "", step = landed()) }
            } catch (e: ApiException) {
                _state.update { it.copy(busy = false, error = otpFailure(e)) }
            }
        }
    }

    /** The first check code. Replacing one takes the reset screen and a biometric. */
    fun submitCheckCode() {
        if (_state.value.busy) return
        val code = validatedCode() ?: return
        _state.update { it.copy(busy = true, error = null) }
        viewModelScope.launch {
            try {
                child.setCheckCode(code, biometricOk = false)
                progress.markCheckCodeSet(memberId)
                _state.update { it.copy(busy = false, code = "", codeAgain = "", step = landed()) }
            } catch (e: ApiException) {
                if (e.isCode(ErrorCodes.BIOMETRIC_REQUIRED)) {
                    progress.markCheckCodeSet(memberId)
                    _state.update {
                        it.copy(
                            busy = false,
                            code = "",
                            codeAgain = "",
                            step = landed(),
                            notice = UiText(R.string.child_code_exists),
                        )
                    }
                } else {
                    _state.update { it.copy(busy = false, error = ErrorMessages.of(e)) }
                }
            }
        }
    }

    fun requestReset() {
        _state.update {
            it.copy(
                resetOpen = true,
                resetUnlocked = false,
                pendingBiometric = BiometricPurpose.RESET_CODE,
                code = "",
                codeAgain = "",
                error = null,
                revealedCode = null,
            )
        }
    }

    fun closeReset() {
        _state.update {
            it.copy(resetOpen = false, resetUnlocked = false, pendingBiometric = null, code = "", codeAgain = "")
        }
    }

    fun submitReset() {
        if (_state.value.busy || !_state.value.resetUnlocked) return
        val code = validatedCode() ?: return
        _state.update { it.copy(busy = true, error = null) }
        viewModelScope.launch {
            try {
                child.setCheckCode(code, biometricOk = true)
                progress.markCheckCodeSet(memberId)
                _state.update {
                    it.copy(
                        busy = false,
                        code = "",
                        codeAgain = "",
                        resetOpen = false,
                        resetUnlocked = false,
                        notice = UiText(R.string.child_reset_done),
                    )
                }
            } catch (e: ApiException) {
                _state.update { it.copy(busy = false, error = ErrorMessages.of(e)) }
            }
        }
    }

    fun openAlert(caseId: String) {
        if (!ChildRules.isCaseId(caseId)) return
        _state.update {
            it.copy(caseId = caseId, prompt = true, revealedCode = null, callFallback = false, error = null)
        }
        viewModelScope.launch { reload(caseId) }
    }

    fun showPrompt() {
        val case = _state.value.case ?: return
        if (!ChildRules.isOpen(case.state)) return
        _state.update { it.copy(prompt = true, revealedCode = null, callFallback = false) }
    }

    /**
     * Leaves the question without posting. The case stays open so the backend
     * can fall through to the call when the push window ends.
     */
    fun notNow() {
        _state.update {
            it.copy(prompt = false, pendingBiometric = null, revealedCode = null, callFallback = false)
        }
    }

    fun requestYes() = ask(BiometricPurpose.ANSWER_YES)

    fun requestNo() = ask(BiometricPurpose.ANSWER_NO)

    fun requestReveal() {
        if (!ChildRules.canRevealCode(_state.value.case?.state)) return
        ask(BiometricPurpose.REVEAL_CODE)
    }

    fun hideCode() = _state.update { it.copy(revealedCode = null, callFallback = false) }

    fun onBiometricResult(ok: Boolean) {
        val purpose = _state.value.pendingBiometric ?: return
        _state.update { it.copy(pendingBiometric = null) }
        if (!ok) return
        when (purpose) {
            BiometricPurpose.ANSWER_YES -> postAnswer("yes")
            BiometricPurpose.ANSWER_NO -> postAnswer("no")
            BiometricPurpose.REVEAL_CODE -> fetchCode()
            BiometricPurpose.RESET_CODE -> _state.update {
                it.copy(resetOpen = true, resetUnlocked = true, code = "", codeAgain = "", error = null)
            }
        }
    }

    fun setVisible(visible: Boolean) {
        poll?.cancel()
        poll = null
        if (!visible) return
        poll = viewModelScope.launch { pollWhileOpen() }
    }

    private fun ask(purpose: BiometricPurpose) {
        if (_state.value.busy) return
        val caseState = _state.value.case?.state
        val allowed = when (purpose) {
            BiometricPurpose.ANSWER_YES, BiometricPurpose.ANSWER_NO -> ChildRules.canAnswer(caseState)
            BiometricPurpose.REVEAL_CODE -> ChildRules.canRevealCode(caseState)
            BiometricPurpose.RESET_CODE -> true
        }
        if (!allowed) return
        _state.update { it.copy(pendingBiometric = purpose, error = null) }
    }

    private fun postAnswer(answer: String) {
        val id = _state.value.caseId ?: return
        if (!ChildRules.canAnswer(_state.value.case?.state)) return
        _state.update { it.copy(busy = true, error = null) }
        viewModelScope.launch {
            try {
                val fresh = child.answer(id, answer)
                _state.update {
                    it.copy(
                        busy = false,
                        case = fresh,
                        prompt = ChildRules.isOpen(fresh.state),
                        revealedCode = null,
                        callFallback = false,
                    )
                }
            } catch (e: ApiException) {
                if (e is ApiException.Http && e.status == 401) return@launch
                _state.update { it.copy(busy = false, error = ErrorMessages.of(e)) }
            }
        }
    }

    private fun fetchCode() {
        val id = _state.value.caseId ?: return
        if (!ChildRules.canRevealCode(_state.value.case?.state)) return
        viewModelScope.launch {
            try {
                val body = child.callCode(id)
                val digits = body.code?.takeIf { ChildRules.isOtp(it) }
                _state.update { it.copy(revealedCode = digits, callFallback = digits == null, error = null) }
            } catch (e: ApiException) {
                if (e is ApiException.Http && e.status == 401) return@launch
                _state.update { it.copy(revealedCode = null, callFallback = false, error = ErrorMessages.of(e)) }
            }
        }
    }

    private suspend fun pollWhileOpen() {
        while (coroutineContext.isActive) {
            val id = _state.value.caseId
            val existing = _state.value.case
            if (id == null) {
                delay(pollEvery)
                continue
            }
            if (existing != null && !ChildRules.isOpen(existing.state)) return
            reload(id)
            if (!ChildRules.isOpen(_state.value.case?.state)) return
            delay(pollEvery)
        }
    }

    private suspend fun reload(caseId: String) {
        try {
            val fresh = child.loadCase(caseId)
            _state.update { current ->
                val stillCalling = fresh.state == "calling"
                current.copy(
                    case = fresh,
                    revealedCode = if (stillCalling) current.revealedCode else null,
                    callFallback = if (stillCalling) current.callFallback else false,
                    prompt = if (ChildRules.isOpen(fresh.state)) current.prompt else false,
                    error = null,
                )
            }
        } catch (e: ApiException) {
            if (e is ApiException.Http && e.status == 401) return
            _state.update { it.copy(error = ErrorMessages.of(e)) }
        }
    }

    private fun validatedCode(): String? {
        val first = _state.value.code
        val second = _state.value.codeAgain
        if (!ChildRules.isCheckCode(first)) {
            _state.update { it.copy(error = UiText(R.string.error_invalid_code)) }
            return null
        }
        if (!ChildRules.checkCodesMatch(first, second)) {
            _state.update { it.copy(error = UiText(R.string.child_code_mismatch)) }
            return null
        }
        return first
    }

    private fun landed(): ChildRules.Step =
        ChildRules.step(_state.value.status, progress.isPhoneVerified(memberId), progress.isCheckCodeSet(memberId))

    private fun otpFailure(error: ApiException): UiText = when {
        error.isCode(ErrorCodes.RATE_LIMITED) -> UiText(R.string.error_otp_rate_limited)
        error.isCode(ErrorCodes.OTP_UNAVAILABLE) -> UiText(R.string.error_otp_unavailable)
        error.isCode(ErrorCodes.SMS_FAILED) -> UiText(R.string.error_otp_sms_failed)
        error.isCode(ErrorCodes.OTP_WRONG) -> UiText(R.string.error_otp_wrong)
        error.isCode(ErrorCodes.OTP_EXPIRED) -> UiText(R.string.error_otp_expired)
        else -> ErrorMessages.of(error)
    }

    override fun onCleared() {
        poll?.cancel()
    }
}
