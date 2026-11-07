package com.familyshield.app.ui.family

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.familyshield.app.R
import com.familyshield.app.data.api.CaseSummary
import com.familyshield.app.data.api.Member
import com.familyshield.app.data.api.ParentCase
import com.familyshield.app.domain.CaseColor
import com.familyshield.app.domain.ChildStage
import com.familyshield.app.domain.MemberRules
import com.familyshield.app.domain.Times
import com.familyshield.app.ui.common.ErrorText
import com.familyshield.app.ui.common.FailureBox
import com.familyshield.app.ui.common.LoadingBox
import com.familyshield.app.ui.common.NoticeText
import com.familyshield.app.ui.common.UiText
import com.familyshield.app.ui.common.copyText
import com.familyshield.app.ui.common.shareText
import java.time.Instant

@Composable
fun FamilyRoute(
    viewModel: FamilyViewModel,
    familyName: String,
    onOpenCase: (ParentCase) -> Unit,
    onOpenRecent: (String) -> Unit,
    onSignOut: () -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    if (state.page == FamilyPage.NewCase) {
        NewCaseContent(
            state = state,
            members = state.members.filter { MemberRules.canVerify(it) },
            onBack = viewModel::closeNewCase,
            onSelect = viewModel::selectChild,
            onText = viewModel::setCaseText,
            onVerify = { viewModel.verify(onOpenCase) },
            onRemoveAudio = viewModel::removeDraftAudio,
        )
        return
    }
    FamilyHomeContent(
        familyName = familyName,
        state = state,
        onRefresh = { viewModel.refresh() },
        onSignOut = onSignOut,
        onAdd = { viewModel.showAdd(true) },
        onVerifyChild = {
            viewModel.selectChild(it)
            viewModel.openNewCase()
            viewModel.selectChild(it)
        },
        onNewCase = viewModel::openNewCase,
        onConfirmJoin = viewModel::confirmJoin,
        onRejectJoin = viewModel::rejectJoin,
        onConfirmPhone = viewModel::confirmPhone,
        onRejectPhone = viewModel::rejectPhone,
        onReissue = viewModel::reissue,
        onCallOnly = { viewModel.showCallOnly(it) },
        onOpenRecent = { onOpenRecent(it.id) },
    )
    val context = LocalContext.current
    state.invite?.let { invite ->
        val expires = Times.shortDateTime(invite.expiresAt, LocalConfiguration.current.locales[0])
        InviteDialog(
            invite = invite,
            expiresLabel = expires,
            onCopy = {
                copyText(
                    context,
                    context.getString(R.string.invite_clip_label),
                    invite.secret,
                    sensitive = true,
                )
            },
            onShare = {
                shareText(
                    context,
                    context.getString(R.string.invite_share_title),
                    context.getString(R.string.invite_share_text, invite.secret),
                )
            },
            onDone = viewModel::dismissInvite,
        )
    }
    if (state.showAdd) {
        AddChildDialog(
            state = state,
            onName = viewModel::setAddName,
            onPhone = viewModel::setAddPhone,
            onByPhone = viewModel::setAddByPhone,
            onSubmit = viewModel::addChild,
            onDismiss = { viewModel.showAdd(false) },
        )
    }
    val callOnlyId = state.callOnlyMemberId
    if (callOnlyId != null) {
        val name = state.members.firstOrNull { it.id == callOnlyId }?.displayName.orEmpty()
        CallOnlyDialog(
            name = name,
            phone = state.addPhone,
            busy = state.busy,
            error = state.error,
            onPhone = viewModel::setAddPhone,
            onSubmit = viewModel::submitCallOnly,
            onDismiss = { viewModel.showCallOnly(null) },
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FamilyHomeContent(
    familyName: String,
    state: FamilyUiState,
    onRefresh: () -> Unit,
    onSignOut: () -> Unit,
    onAdd: () -> Unit,
    onVerifyChild: (String) -> Unit,
    onNewCase: () -> Unit,
    onConfirmJoin: (String) -> Unit,
    onRejectJoin: (String) -> Unit,
    onConfirmPhone: (String) -> Unit,
    onRejectPhone: (String) -> Unit,
    onReissue: (String) -> Unit,
    onCallOnly: (String) -> Unit,
    onOpenRecent: (CaseSummary) -> Unit,
    now: Instant = Instant.now(),
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(familyName.ifBlank { stringResource(R.string.family_title_fallback) }) },
                actions = {
                    TextButton(onClick = onRefresh, modifier = Modifier.testTag("refresh")) {
                        Text(stringResource(R.string.cd_refresh))
                    }
                    TextButton(onClick = onSignOut) { Text(stringResource(R.string.action_sign_out)) }
                },
            )
        },
    ) { padding ->
        when {
            state.loading && state.members.isEmpty() && state.error == null -> LoadingBox(Modifier.padding(padding))
            state.error != null && state.members.isEmpty() ->
                FailureBox(state.error, onRefresh, Modifier.padding(padding))
            else -> Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp)
                    .testTag("family_home"),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                state.notice?.let { NoticeText(it) }
                if (state.error != null && state.members.isNotEmpty()) ErrorText(state.error)
                Text(stringResource(R.string.family_children_heading), style = MaterialTheme.typography.titleMedium)
                val children = state.members.filter { MemberRules.isChild(it) }
                if (children.isEmpty()) {
                    Text(stringResource(R.string.family_empty_title), style = MaterialTheme.typography.titleLarge)
                    Text(stringResource(R.string.family_empty_body))
                } else {
                    children.forEach { member ->
                        ChildCard(
                            member = member,
                            now = now,
                            busy = state.busy,
                            onVerify = { onVerifyChild(member.id) },
                            onConfirmJoin = { onConfirmJoin(member.id) },
                            onRejectJoin = { onRejectJoin(member.id) },
                            onConfirmPhone = { onConfirmPhone(member.id) },
                            onRejectPhone = { onRejectPhone(member.id) },
                            onReissue = { onReissue(member.id) },
                            onCallOnly = { onCallOnly(member.id) },
                        )
                    }
                }
                Button(
                    onClick = onAdd,
                    modifier = Modifier.fillMaxWidth().testTag("add_child"),
                ) { Text(stringResource(R.string.family_add_child)) }
                Button(
                    onClick = onNewCase,
                    modifier = Modifier.fillMaxWidth().testTag("verify_message"),
                ) { Text(stringResource(R.string.family_verify_message)) }
                HorizontalDivider()
                Text(stringResource(R.string.family_recent_heading), style = MaterialTheme.typography.titleMedium)
                if (state.recent.isEmpty()) {
                    Text(stringResource(R.string.family_recent_empty))
                } else {
                    state.recent.forEach { summary ->
                        RecentRow(summary, onClick = { onOpenRecent(summary) })
                    }
                }
            }
        }
    }
}

@Composable
private fun ChildCard(
    member: Member,
    now: Instant,
    busy: Boolean,
    onVerify: () -> Unit,
    onConfirmJoin: () -> Unit,
    onRejectJoin: () -> Unit,
    onConfirmPhone: () -> Unit,
    onRejectPhone: () -> Unit,
    onReissue: () -> Unit,
    onCallOnly: () -> Unit,
) {
    val stage = MemberRules.stage(member, now)
    val canVerify = MemberRules.canVerify(member)
    val locale = LocalConfiguration.current.locales[0]
    val expires = Times.shortDateTime(member.inviteExpiresAt, locale)
    val name = member.displayName.ifBlank { stringResource(R.string.cd_child) }
    val last4 = member.phoneLast4.orEmpty()
    Card(modifier = Modifier.fillMaxWidth().testTag("child_${member.id}")) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(name, style = MaterialTheme.typography.titleMedium)
            Text(statusLine(stage, name, last4, expires))
            if (member.awaitingConfirm) {
                Text(stringResource(R.string.join_request, name, last4))
                Text(stringResource(R.string.join_request_hint))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = onConfirmJoin, enabled = !busy, modifier = Modifier.testTag("confirm_${member.id}")) {
                        Text(stringResource(R.string.action_confirm))
                    }
                    OutlinedButton(onClick = onRejectJoin, enabled = !busy, modifier = Modifier.testTag("reject_${member.id}")) {
                        Text(stringResource(R.string.action_reject))
                    }
                }
            }
            if (MemberRules.hasPendingNumber(member)) {
                val pending = member.pendingPhoneLast4.orEmpty()
                Text(stringResource(R.string.phone_change_request, name, pending))
                Text(stringResource(R.string.phone_change_hint, name))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = onConfirmPhone, enabled = !busy) { Text(stringResource(R.string.action_confirm)) }
                    OutlinedButton(onClick = onRejectPhone, enabled = !busy) { Text(stringResource(R.string.action_reject)) }
                }
            }
            if (MemberRules.canReissueInvite(member)) {
                TextButton(onClick = onReissue, enabled = !busy) { Text(stringResource(R.string.child_new_invite)) }
            }
            if (MemberRules.canAddCallOnly(member)) {
                TextButton(onClick = onCallOnly, enabled = !busy) { Text(stringResource(R.string.child_add_by_phone)) }
            }
            Button(
                onClick = onVerify,
                enabled = canVerify && !busy,
                modifier = Modifier.testTag("verify_${member.id}"),
            ) { Text(stringResource(R.string.action_verify)) }
        }
    }
}

@Composable
private fun statusLine(stage: ChildStage, name: String, last4: String, expires: String): String = when (stage) {
    ChildStage.READY -> if (last4.isBlank()) {
        stringResource(R.string.child_ready_no_number)
    } else {
        stringResource(R.string.child_ready, name, last4)
    }
    ChildStage.AWAITING_CONFIRM -> stringResource(R.string.child_awaiting_confirm, name)
    ChildStage.INVITED -> stringResource(R.string.child_invited, name, expires)
    ChildStage.INVITE_EXPIRED -> stringResource(R.string.child_invite_expired, name)
    ChildStage.JOINED_NO_NUMBER -> stringResource(R.string.child_joined_no_number, name)
    ChildStage.CALL_ONLY_LINK_SENT -> stringResource(R.string.child_call_only_link_sent, name, last4)
    ChildStage.NOT_READY -> stringResource(R.string.child_not_ready, name)
}

@Composable
private fun RecentRow(summary: CaseSummary, onClick: () -> Unit) {
    val color = CaseColor.of(summary.color, summary.decidedAt)
    val label = when (color) {
        CaseColor.OPEN -> stringResource(R.string.case_row_open)
        CaseColor.GREEN -> stringResource(R.string.case_row_green)
        CaseColor.RED -> stringResource(R.string.case_row_red)
        CaseColor.YELLOW -> stringResource(R.string.case_row_yellow)
    }
    val description = when (color) {
        CaseColor.OPEN -> stringResource(R.string.cd_status_open)
        CaseColor.GREEN -> stringResource(R.string.cd_status_green)
        CaseColor.RED -> stringResource(R.string.cd_status_red)
        CaseColor.YELLOW -> stringResource(R.string.cd_status_yellow)
    }
    TextButton(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth().semantics { contentDescription = description }.testTag("case_${summary.id}"),
    ) {
        Text("${summary.childDisplayName} · $label", modifier = Modifier.fillMaxWidth())
    }
}

@Composable
private fun AddChildDialog(
    state: FamilyUiState,
    onName: (String) -> Unit,
    onPhone: (String) -> Unit,
    onByPhone: (Boolean) -> Unit,
    onSubmit: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.add_child_title)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = state.addName,
                    onValueChange = onName,
                    label = { Text(stringResource(R.string.add_child_name_label)) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Words),
                    modifier = Modifier.fillMaxWidth().testTag("child_name"),
                )
                Row(
                    Modifier.fillMaxWidth().selectable(selected = !state.addByPhone, onClick = { onByPhone(false) }),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    RadioButton(selected = !state.addByPhone, onClick = { onByPhone(false) })
                    Text(stringResource(R.string.add_child_mode_app))
                }
                Text(stringResource(R.string.add_child_mode_app_hint), style = MaterialTheme.typography.bodySmall)
                Row(
                    Modifier.fillMaxWidth().selectable(selected = state.addByPhone, onClick = { onByPhone(true) }),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    RadioButton(selected = state.addByPhone, onClick = { onByPhone(true) })
                    Text(stringResource(R.string.add_child_mode_phone))
                }
                if (state.addByPhone) {
                    Text(stringResource(R.string.add_child_mode_phone_hint), style = MaterialTheme.typography.bodySmall)
                    OutlinedTextField(
                        value = state.addPhone,
                        onValueChange = onPhone,
                        label = { Text(stringResource(R.string.add_child_phone_label)) },
                        placeholder = { Text(stringResource(R.string.add_child_phone_example)) },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth().testTag("child_phone"),
                    )
                }
                state.error?.let { ErrorText(it) }
            }
        },
        confirmButton = {
            Button(onClick = onSubmit, enabled = !state.busy, modifier = Modifier.testTag("add_child_submit")) {
                Text(stringResource(R.string.add_child_submit))
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.action_cancel)) } },
    )
}

@Composable
private fun CallOnlyDialog(
    name: String,
    phone: String,
    busy: Boolean,
    error: UiText?,
    onPhone: (String) -> Unit,
    onSubmit: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.call_only_title, name)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(stringResource(R.string.add_child_mode_phone_hint))
                OutlinedTextField(
                    value = phone,
                    onValueChange = onPhone,
                    label = { Text(stringResource(R.string.add_child_phone_label)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                error?.let { ErrorText(it) }
            }
        },
        confirmButton = {
            Button(onClick = onSubmit, enabled = !busy) { Text(stringResource(R.string.call_only_submit)) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.action_cancel)) } },
    )
}

@Composable
private fun InviteDialog(
    invite: ShownInvite,
    expiresLabel: String,
    onCopy: () -> Unit,
    onShare: () -> Unit,
    onDone: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = {},
        title = { Text(stringResource(R.string.invite_title, invite.name)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(stringResource(R.string.invite_body, invite.name))
                Text(invite.secret, style = MaterialTheme.typography.headlineSmall, modifier = Modifier.testTag("invite_secret"))
                if (expiresLabel.isNotBlank()) Text(stringResource(R.string.invite_expires, expiresLabel))
            }
        },
        confirmButton = {
            Row {
                TextButton(onClick = onCopy, modifier = Modifier.testTag("invite_copy")) { Text(stringResource(R.string.action_copy)) }
                TextButton(onClick = onShare, modifier = Modifier.testTag("invite_share")) { Text(stringResource(R.string.action_share)) }
                Button(onClick = onDone) { Text(stringResource(R.string.action_done)) }
            }
        },
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NewCaseContent(
    state: FamilyUiState,
    members: List<Member>,
    onBack: () -> Unit,
    onSelect: (String) -> Unit,
    onText: (String) -> Unit,
    onVerify: () -> Unit,
    onRemoveAudio: () -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.new_case_title)) },
                navigationIcon = {
                    TextButton(onClick = onBack) { Text(stringResource(R.string.cd_back)) }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(stringResource(R.string.new_case_explain))
            if (state.fromShare) {
                Text(stringResource(R.string.new_case_not_sent_yet), modifier = Modifier.testTag("share_held"))
            }
            state.draftAudio?.let { audio ->
                val kilobytes = ((audio.file.length().coerceAtLeast(0L) + 1023L) / 1024L).toInt().coerceAtLeast(1)
                Text(
                    stringResource(R.string.new_case_audio_attached, audio.displayName, kilobytes),
                    modifier = Modifier.testTag("draft_audio"),
                )
                TextButton(onClick = onRemoveAudio, enabled = !state.busy, modifier = Modifier.testTag("remove_audio")) {
                    Text(stringResource(R.string.new_case_audio_remove))
                }
            }
            Text(stringResource(R.string.new_case_child_heading), style = MaterialTheme.typography.titleMedium)
            if (members.isEmpty()) {
                Text(stringResource(R.string.new_case_no_children))
            } else {
                members.forEach { member ->
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .selectable(selected = state.caseChildId == member.id, onClick = { onSelect(member.id) })
                            .testTag("pick_${member.id}"),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        RadioButton(selected = state.caseChildId == member.id, onClick = { onSelect(member.id) })
                        Text(member.displayName)
                    }
                }
            }
            OutlinedTextField(
                value = state.caseText,
                onValueChange = onText,
                label = { Text(stringResource(R.string.new_case_text_label)) },
                supportingText = { Text(stringResource(R.string.new_case_text_hint)) },
                modifier = Modifier.fillMaxWidth().testTag("case_text"),
                minLines = 3,
            )
            Text(stringResource(R.string.new_case_counter, state.caseText.length, FamilyViewModel.TEXT_LIMIT))
            Button(
                onClick = onVerify,
                enabled = !state.busy && members.isNotEmpty(),
                modifier = Modifier.fillMaxWidth().testTag("open_case"),
            ) { Text(stringResource(R.string.new_case_submit)) }
            state.error?.let { ErrorText(it) }
        }
    }
}
