package com.familyshield.app.ui.child

import android.Manifest
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.familyshield.app.R
import com.familyshield.app.data.ChildSource
import com.familyshield.app.data.api.ApiException
import com.familyshield.app.data.api.InviteAccepted
import com.familyshield.app.domain.ChildRules
import com.familyshield.app.ui.call.OutboundLabelCard
import com.familyshield.app.ui.common.ErrorMessages
import com.familyshield.app.ui.common.ErrorText
import com.familyshield.app.ui.common.NoticeText
import com.familyshield.app.ui.common.UiText
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class AcceptInviteUiState(
    val secret: String = "",
    val busy: Boolean = false,
    val error: UiText? = null,
)

class AcceptInviteViewModel(private val child: ChildSource) : ViewModel() {
    private val _state = MutableStateFlow(AcceptInviteUiState())
    val state: StateFlow<AcceptInviteUiState> = _state.asStateFlow()

    fun setSecret(value: String) = _state.update { it.copy(secret = value.take(64), error = null) }

    fun accept(onAccepted: (InviteAccepted) -> Unit) {
        if (_state.value.busy) return
        val secret = ChildRules.normalizeInvite(_state.value.secret)
        if (!ChildRules.inviteLooksValid(secret)) {
            _state.update { it.copy(error = UiText(R.string.error_invite_invalid)) }
            return
        }
        _state.update { it.copy(busy = true, error = null) }
        viewModelScope.launch {
            try {
                val accepted = child.acceptInvite(secret)
                _state.update { it.copy(busy = false, secret = "") }
                onAccepted(accepted)
            } catch (e: ApiException) {
                _state.update { it.copy(busy = false, error = ErrorMessages.of(e)) }
            }
        }
    }
}

@Composable
fun ChildRoute(
    viewModel: ChildViewModel,
    biometric: BiometricGate,
    onSignOut: () -> Unit,
    onRefreshMembership: () -> Unit,
    shareNotice: String? = null,
    onDiscardShare: (() -> Unit)? = null,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val activity = LocalContext.current as? FragmentActivity
    val purpose = state.pendingBiometric
    LaunchedEffect(purpose) {
        if (purpose == null) return@LaunchedEffect
        val host = activity
        if (host == null) {
            viewModel.onBiometricResult(false)
            return@LaunchedEffect
        }
        biometric.confirm(host, purpose, viewModel::onBiometricResult)
    }
    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { }
    LaunchedEffect(state.step) {
        if (Build.VERSION.SDK_INT >= 33 &&
            (state.step == ChildRules.Step.HOME || state.step == ChildRules.Step.WAITING)
        ) {
            permission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    DisposableEffect(lifecycle, viewModel) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_START -> viewModel.setVisible(true)
                Lifecycle.Event.ON_STOP -> viewModel.setVisible(false)
                else -> Unit
            }
        }
        lifecycle.addObserver(observer)
        if (lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED)) viewModel.setVisible(true)
        onDispose {
            lifecycle.removeObserver(observer)
            viewModel.setVisible(false)
        }
    }
    val open = state.case?.takeIf { ChildRules.isOpen(it.state) }
    when {
        state.step == ChildRules.Step.PHONE -> ChildPhoneContent(
            phone = state.phone,
            busy = state.busy,
            error = state.error,
            notice = state.notice,
            onPhone = viewModel::setPhone,
            onSubmit = viewModel::submitPhone,
            onSignOut = onSignOut,
        )
        state.step == ChildRules.Step.OTP -> ChildOtpContent(
            otp = state.otp,
            last4 = state.phoneLast4,
            busy = state.busy,
            error = state.error,
            onOtp = viewModel::setOtp,
            onSubmit = viewModel::submitOtp,
            onResend = viewModel::resendOtp,
            onVoice = viewModel::callWithOtp,
            onSignOut = onSignOut,
        )
        state.step == ChildRules.Step.CHECK_CODE -> ChildCheckCodeContent(
            code = state.code,
            again = state.codeAgain,
            busy = state.busy,
            error = state.error,
            notice = state.notice,
            onCode = viewModel::setCode,
            onAgain = viewModel::setCodeAgain,
            onSubmit = viewModel::submitCheckCode,
            onSignOut = onSignOut,
        )
        state.step == ChildRules.Step.WAITING -> ChildWaitingContent(
            familyName = state.familyName,
            last4 = state.phoneLast4,
            notice = state.notice,
            error = state.error,
            onRefresh = onRefreshMembership,
            onSignOut = onSignOut,
        )
        state.step == ChildRules.Step.HOME && state.resetOpen -> ChildResetContent(
            unlocked = state.resetUnlocked,
            code = state.code,
            again = state.codeAgain,
            busy = state.busy,
            error = state.error,
            onUnlock = viewModel::requestReset,
            onCode = viewModel::setCode,
            onAgain = viewModel::setCodeAgain,
            onSubmit = viewModel::submitReset,
            onClose = viewModel::closeReset,
        )
        state.step == ChildRules.Step.HOME && state.prompt && open != null -> QuestionContent(
            calling = ChildRules.canRevealCode(open.state),
            revealedCode = state.revealedCode,
            callFallback = state.callFallback,
            busy = state.busy,
            error = state.error,
            onYes = viewModel::requestYes,
            onNo = viewModel::requestNo,
            onNotNow = viewModel::notNow,
            onReveal = viewModel::requestReveal,
            onHideCode = viewModel::hideCode,
            askerName = open.askerDisplayName,
            requestAmount = open.requestAmount,
        )
        else -> ChildHomeContent(
            familyName = state.familyName,
            waiting = open != null,
            decided = decidedLine(state.case),
            notice = state.notice,
            error = state.error,
            shareNotice = shareNotice,
            onAnswer = viewModel::showPrompt,
            onReset = viewModel::requestReset,
            onSignOut = onSignOut,
            onDiscardShare = onDiscardShare,
            onDismissNotice = viewModel::dismissNotice,
        )
    }
}

@Composable
private fun decidedLine(case: com.familyshield.app.data.api.ChildCase?): String? {
    case ?: return null
    if (ChildRules.isOpen(case.state)) return null
    val res = when (case.result) {
        "sent" -> R.string.child_result_yes
        "not_sent" -> R.string.child_result_no
        else -> R.string.child_result_closed
    }
    return stringResource(res)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AcceptInviteContent(
    state: AcceptInviteUiState,
    onSecret: (String) -> Unit,
    onAccept: () -> Unit,
    onBack: () -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.invite_entry_title)) },
                navigationIcon = {
                    TextButton(onClick = onBack) { Text(stringResource(R.string.cd_back)) }
                },
            )
        },
    ) { padding ->
        FormColumn(Modifier.padding(padding)) {
            Text(stringResource(R.string.invite_entry_body), style = MaterialTheme.typography.bodyLarge)
            OutlinedTextField(
                value = state.secret,
                onValueChange = onSecret,
                label = { Text(stringResource(R.string.invite_entry_label)) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth().testTag("invite_secret"),
            )
            Button(
                onClick = onAccept,
                enabled = !state.busy,
                modifier = Modifier.fillMaxWidth().testTag("accept_invite"),
            ) { Text(stringResource(R.string.invite_entry_submit)) }
            state.error?.let { ErrorText(it) }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChildPhoneContent(
    phone: String,
    busy: Boolean,
    error: UiText?,
    notice: UiText?,
    onPhone: (String) -> Unit,
    onSubmit: () -> Unit,
    onSignOut: () -> Unit,
) {
    ChildScaffold(stringResource(R.string.child_phone_title), onSignOut) {
        Text(stringResource(R.string.child_phone_body), style = MaterialTheme.typography.bodyLarge)
        OutlinedTextField(
            value = phone,
            onValueChange = onPhone,
            label = { Text(stringResource(R.string.child_phone_label)) },
            placeholder = { Text(stringResource(R.string.add_child_phone_example)) },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
            modifier = Modifier.fillMaxWidth().testTag("child_phone"),
        )
        Button(
            onClick = onSubmit,
            enabled = !busy,
            modifier = Modifier.fillMaxWidth().testTag("send_otp"),
        ) { Text(stringResource(R.string.child_phone_submit)) }
        notice?.let { NoticeText(it) }
        error?.let { ErrorText(it) }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChildOtpContent(
    otp: String,
    last4: String?,
    busy: Boolean,
    error: UiText?,
    onOtp: (String) -> Unit,
    onSubmit: () -> Unit,
    onResend: () -> Unit,
    onVoice: () -> Unit,
    onSignOut: () -> Unit,
) {
    ChildScaffold(stringResource(R.string.child_otp_title), onSignOut) {
        Text(
            if (last4 != null) stringResource(R.string.child_otp_body, last4) else stringResource(R.string.child_otp_body_plain),
            style = MaterialTheme.typography.bodyLarge,
        )
        OutlinedTextField(
            value = otp,
            onValueChange = onOtp,
            label = { Text(stringResource(R.string.child_otp_label)) },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth().testTag("child_otp"),
        )
        Button(
            onClick = onSubmit,
            enabled = !busy,
            modifier = Modifier.fillMaxWidth().testTag("check_otp"),
        ) { Text(stringResource(R.string.child_otp_submit)) }
        TextButton(onClick = onResend, enabled = !busy, modifier = Modifier.testTag("resend_otp")) {
            Text(stringResource(R.string.child_otp_resend))
        }
        TextButton(onClick = onVoice, enabled = !busy, modifier = Modifier.testTag("voice_otp")) {
            Text(stringResource(R.string.child_otp_voice))
        }
        error?.let { ErrorText(it) }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChildCheckCodeContent(
    code: String,
    again: String,
    busy: Boolean,
    error: UiText?,
    notice: UiText?,
    onCode: (String) -> Unit,
    onAgain: (String) -> Unit,
    onSubmit: () -> Unit,
    onSignOut: () -> Unit,
) {
    ChildScaffold(stringResource(R.string.child_code_title), onSignOut) {
        Text(stringResource(R.string.child_code_body), style = MaterialTheme.typography.bodyLarge)
        CheckCodeFields(code, again, onCode, onAgain)
        Button(
            onClick = onSubmit,
            enabled = !busy,
            modifier = Modifier.fillMaxWidth().testTag("save_check_code"),
        ) { Text(stringResource(R.string.child_code_submit)) }
        notice?.let { NoticeText(it) }
        error?.let { ErrorText(it) }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChildWaitingContent(
    familyName: String,
    last4: String?,
    notice: UiText?,
    error: UiText?,
    onRefresh: () -> Unit,
    onSignOut: () -> Unit,
) {
    ChildScaffold(familyName.ifBlank { stringResource(R.string.family_title_fallback) }, onSignOut) {
        Text(stringResource(R.string.child_waiting_title), style = MaterialTheme.typography.headlineSmall)
        Text(
            if (last4 != null) stringResource(R.string.child_waiting_body_number, last4)
            else stringResource(R.string.child_waiting_body),
            style = MaterialTheme.typography.bodyLarge,
        )
        Button(onClick = onRefresh, modifier = Modifier.testTag("refresh_membership")) {
            Text(stringResource(R.string.child_waiting_refresh))
        }
        OutboundLabelCard()
        notice?.let { NoticeText(it) }
        error?.let { ErrorText(it) }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChildHomeContent(
    familyName: String,
    waiting: Boolean,
    decided: String?,
    notice: UiText?,
    error: UiText?,
    shareNotice: String?,
    onAnswer: () -> Unit,
    onReset: () -> Unit,
    onSignOut: () -> Unit,
    onDiscardShare: (() -> Unit)?,
    onDismissNotice: () -> Unit,
) {
    ChildScaffold(familyName.ifBlank { stringResource(R.string.family_title_fallback) }, onSignOut) {
        if (waiting) {
            Text(stringResource(R.string.child_home_waiting), style = MaterialTheme.typography.bodyLarge)
            Button(onClick = onAnswer, modifier = Modifier.fillMaxWidth().testTag("answer_request")) {
                Text(stringResource(R.string.child_home_answer))
            }
        } else {
            Text(
                stringResource(R.string.child_home_idle),
                style = MaterialTheme.typography.bodyLarge,
                modifier = Modifier.testTag("child_idle"),
            )
        }
        decided?.let { Text(it, modifier = Modifier.testTag("child_decided")) }
        notice?.let {
            NoticeText(it)
            TextButton(onClick = onDismissNotice) { Text(stringResource(R.string.action_done)) }
        }
        error?.let { ErrorText(it) }
        if (shareNotice != null) {
            Text(shareNotice, modifier = Modifier.testTag("share_needs_parent"))
            if (onDiscardShare != null) {
                TextButton(onClick = onDiscardShare) { Text(stringResource(R.string.share_discard)) }
            }
        }
        TextButton(onClick = onReset, modifier = Modifier.testTag("reset_check_code")) {
            Text(stringResource(R.string.child_home_reset))
        }
        OutboundLabelCard()
    }
}

@Composable
fun QuestionContent(
    calling: Boolean,
    revealedCode: String?,
    callFallback: Boolean,
    busy: Boolean,
    error: UiText?,
    onYes: () -> Unit,
    onNo: () -> Unit,
    onNotNow: () -> Unit,
    onReveal: () -> Unit,
    onHideCode: () -> Unit,
    askerName: String? = null,
    requestAmount: String? = null,
    initialChoice: String? = null,
) {
    val palette = com.familyshield.app.ui.theme.LocalFsPalette.current
    var choice by remember { mutableStateOf(initialChoice) }
    val asker = askerName?.takeIf { it.isNotBlank() }
    val amount = requestAmount?.takeIf { it.isNotBlank() }
    Column(Modifier.fillMaxSize().background(palette.bg)) {
    Column(
        Modifier
            .weight(1f)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp),
    ) {
        Row(Modifier.fillMaxWidth().padding(top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier.size(44.dp).testTag("not_now").clickable(onClick = onNotNow),
                contentAlignment = Alignment.Center,
            ) { com.familyshield.app.ui.v3.CloseIcon(palette.text) }
            Text(
                stringResource(R.string.child_request_title),
                modifier = Modifier.weight(1f),
                color = palette.text,
                fontFamily = com.familyshield.app.ui.theme.Pretendard,
                fontWeight = FontWeight(650),
                fontSize = 17.sp,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.size(44.dp))
        }
        if (asker != null) {
            Row(Modifier.padding(top = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                com.familyshield.app.ui.v3.InitialAvatar(asker, size = 52.dp)
                Column(Modifier.padding(start = 12.dp)) {
                    Text(asker, color = palette.text, fontFamily = com.familyshield.app.ui.theme.Pretendard, fontWeight = FontWeight(650), fontSize = 20.sp)
                    Text(stringResource(R.string.child_asker_subtitle, asker), color = palette.muted, fontFamily = com.familyshield.app.ui.theme.Pretendard, fontSize = 14.sp)
                }
            }
        }
        Text(
            if (asker != null || amount != null) stringResource(R.string.child_question_short) else stringResource(R.string.child_question),
            color = palette.text,
            fontFamily = com.familyshield.app.ui.theme.Pretendard,
            fontWeight = FontWeight(700),
            fontSize = 32.sp,
            lineHeight = 40.sp,
            modifier = Modifier.padding(top = 20.dp).testTag("child_question"),
        )
        if (amount != null) {
            Column(
                Modifier.padding(top = 16.dp).fillMaxWidth().clip(androidx.compose.foundation.shape.RoundedCornerShape(24.dp)).background(palette.surface).padding(20.dp),
            ) {
                Text(stringResource(R.string.child_amount_label), color = palette.muted, fontFamily = com.familyshield.app.ui.theme.Pretendard, fontSize = 14.sp)
                Text(amount, color = palette.text, fontFamily = com.familyshield.app.ui.theme.Pretendard, fontWeight = FontWeight(650), fontSize = 42.sp, lineHeight = 52.sp)
                Text(stringResource(R.string.child_amount_source), color = palette.muted, fontFamily = com.familyshield.app.ui.theme.Pretendard, fontSize = 14.sp, modifier = Modifier.padding(top = 8.dp))
            }
        }
        Row(Modifier.padding(top = 16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            AnswerTile(stringResource(R.string.child_yes), stringResource(R.string.v3_yes_detail), choice == "yes", "answer_yes", Modifier.weight(1f)) { choice = "yes" }
            AnswerTile(stringResource(R.string.child_no), stringResource(R.string.v3_no_detail), choice == "no", "answer_no", Modifier.weight(1f)) { choice = "no" }
        }
        if (calling) {
            Text(stringResource(R.string.child_reveal_hint), color = palette.muted, fontFamily = com.familyshield.app.ui.theme.Pretendard, modifier = Modifier.padding(top = 16.dp))
            if (revealedCode != null) {
                val label = stringResource(R.string.cd_one_time_code)
                Text(
                    revealedCode,
                    fontFamily = com.familyshield.app.ui.theme.Pretendard,
                    fontWeight = FontWeight.Bold,
                    fontSize = 40.sp,
                    textAlign = TextAlign.Center,
                    color = palette.text,
                    modifier = Modifier.fillMaxWidth().testTag("one_time_code").semantics { contentDescription = label },
                )
                Text(stringResource(R.string.child_code_shown), color = palette.muted, fontFamily = com.familyshield.app.ui.theme.Pretendard)
                TextButton(onClick = onHideCode, modifier = Modifier.testTag("hide_code")) { Text(stringResource(R.string.child_hide_code)) }
            } else {
                Button(onClick = onReveal, enabled = !busy, modifier = Modifier.fillMaxWidth().testTag("reveal_code")) {
                    Text(stringResource(R.string.child_reveal))
                }
                if (callFallback) {
                    Text(stringResource(R.string.child_fallback_static), modifier = Modifier.testTag("call_fallback"), color = palette.text)
                }
            }
        }
        error?.let { ErrorText(it) }
        Spacer(Modifier.size(24.dp))
    }
        val submitLabel = stringResource(R.string.child_submit_bio)
        com.familyshield.app.ui.v3.LimeButton(
            label = submitLabel,
            enabled = choice != null && !busy,
            onClick = { if (choice == "yes") onYes() else if (choice == "no") onNo() },
            modifier = Modifier.padding(start = 20.dp, end = 20.dp, bottom = 24.dp).testTag("answer_submit"),
            leading = { com.familyshield.app.ui.v3.FaceIcon(palette.ink) },
        )
    }
}

@Composable
private fun AnswerTile(title: String, detail: String, selected: Boolean, tag: String, modifier: Modifier, onClick: () -> Unit) {
    val palette = com.familyshield.app.ui.theme.LocalFsPalette.current
    val bg = if (selected) palette.ink else palette.surface
    val fg = if (selected) palette.bg else palette.text
    val muted = if (selected) palette.heroMuted else palette.muted
    Column(
        modifier
            .clip(androidx.compose.foundation.shape.RoundedCornerShape(20.dp))
            .background(bg)
            .clickable(onClick = onClick)
            .testTag(tag)
            .padding(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(title, color = fg, fontFamily = com.familyshield.app.ui.theme.Pretendard, fontWeight = FontWeight(700), fontSize = 22.sp, modifier = Modifier.weight(1f))
            if (selected) com.familyshield.app.ui.v3.CheckIcon(fg)
        }
        Text(detail, color = muted, fontFamily = com.familyshield.app.ui.theme.Pretendard, fontSize = 14.sp, modifier = Modifier.padding(top = 4.dp))
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChildResetContent(
    unlocked: Boolean,
    code: String,
    again: String,
    busy: Boolean,
    error: UiText?,
    onUnlock: () -> Unit,
    onCode: (String) -> Unit,
    onAgain: (String) -> Unit,
    onSubmit: () -> Unit,
    onClose: () -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.child_reset_title)) },
                navigationIcon = {
                    TextButton(onClick = onClose) { Text(stringResource(R.string.action_cancel)) }
                },
            )
        },
    ) { padding ->
        FormColumn(Modifier.padding(padding)) {
            Text(stringResource(R.string.child_reset_body), style = MaterialTheme.typography.bodyLarge)
            if (!unlocked) {
                Button(onClick = onUnlock, modifier = Modifier.fillMaxWidth().testTag("reset_unlock")) {
                    Text(stringResource(R.string.child_reset_unlock))
                }
            } else {
                CheckCodeFields(code, again, onCode, onAgain)
                Button(
                    onClick = onSubmit,
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth().testTag("reset_save"),
                ) { Text(stringResource(R.string.child_reset_submit)) }
            }
            error?.let { ErrorText(it) }
        }
    }
}

@Composable
private fun CheckCodeFields(
    code: String,
    again: String,
    onCode: (String) -> Unit,
    onAgain: (String) -> Unit,
) {
    OutlinedTextField(
        value = code,
        onValueChange = onCode,
        label = { Text(stringResource(R.string.child_code_label)) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
        visualTransformation = PasswordVisualTransformation(),
        modifier = Modifier.fillMaxWidth().testTag("check_code"),
    )
    OutlinedTextField(
        value = again,
        onValueChange = onAgain,
        label = { Text(stringResource(R.string.child_code_again_label)) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
        visualTransformation = PasswordVisualTransformation(),
        modifier = Modifier.fillMaxWidth().testTag("check_code_again"),
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ChildScaffold(title: String, onSignOut: () -> Unit, content: @Composable () -> Unit) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(title) },
                actions = {
                    TextButton(onClick = onSignOut) { Text(stringResource(R.string.action_sign_out)) }
                },
            )
        },
    ) { padding ->
        FormColumn(Modifier.padding(padding)) { content() }
    }
}

@Composable
private fun FormColumn(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) { content() }
}
