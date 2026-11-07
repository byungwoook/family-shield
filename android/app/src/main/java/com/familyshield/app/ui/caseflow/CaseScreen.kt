package com.familyshield.app.ui.caseflow

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.familyshield.app.R
import com.familyshield.app.data.api.Claims
import com.familyshield.app.data.api.ParentCase
import com.familyshield.app.domain.CaseColor
import com.familyshield.app.domain.CaseCopy
import com.familyshield.app.domain.Times
import com.familyshield.app.ui.common.ErrorText
import com.familyshield.app.ui.common.LoadingBox
import com.familyshield.app.ui.common.copyText
import com.familyshield.app.ui.common.shareText
import com.familyshield.app.ui.theme.LocalResultTones

@Composable
fun CaseRoute(viewModel: CaseViewModel, onBack: () -> Unit) {
    val state by viewModel.state.collectAsStateWithLifecycle()
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
    val current = state.case
    if (state.loading && current == null) {
        LoadingBox()
        return
    }
    if (current == null) {
        state.error?.let { ErrorText(it, Modifier.padding(24.dp)) }
        return
    }
    CaseContent(case = current, pollError = state.error != null, onBack = onBack)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CaseContent(case: ParentCase, pollError: Boolean, onBack: () -> Unit) {
    val color = CaseColor.of(case.color, case.decidedAt)
    val tone = LocalResultTones.current.of(color)
    val locale = LocalConfiguration.current.locales[0]
    val context = LocalContext.current
    val name = case.childDisplayName.ifBlank { stringResource(R.string.cd_child) }
    val whenLabel = Times.shortTime(case.decidedAt, locale)
    val statusCd = when (color) {
        CaseColor.OPEN -> stringResource(R.string.cd_status_open)
        CaseColor.GREEN -> stringResource(R.string.cd_status_green)
        CaseColor.RED -> stringResource(R.string.cd_status_red)
        CaseColor.YELLOW -> stringResource(R.string.cd_status_yellow)
    }
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.case_title, name)) },
                navigationIcon = { TextButton(onClick = onBack) { Text(stringResource(R.string.cd_back)) } },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp)
                .testTag("case_screen"),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (color == CaseColor.OPEN) {
                Text(
                    stringResource(R.string.case_dont_send),
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.testTag("dont_send"),
                )
                Text(stringResource(CaseCopy.openLine(case.state), name))
            }
            val copy = CaseCopy.result(color, case.result)
            if (copy != null) {
                Card(
                    colors = CardDefaults.cardColors(containerColor = tone.container, contentColor = tone.content),
                    modifier = Modifier.fillMaxWidth().semantics { contentDescription = statusCd }.testTag("result_card"),
                ) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(stringResource(copy.title), style = MaterialTheme.typography.titleLarge, modifier = Modifier.testTag("result_title"))
                        Text(stringResource(copy.body, name, whenLabel), modifier = Modifier.testTag("result_body"))
                        if (whenLabel.isNotBlank()) Text(stringResource(R.string.case_checked_at, whenLabel))
                    }
                }
            }
            val pattern = CaseCopy.patternLabel(case.patternId)
            if (pattern != null) {
                Text(stringResource(CaseCopy.patternLine(color), stringResource(pattern), name))
            }
            if (CaseCopy.offersFamilyAlert(color)) {
                val story = case.claims?.story?.takeUnless { it.isBlank() || it.equals("unknown", ignoreCase = true) }
                val message = if (story == null) {
                    stringResource(R.string.family_alert_message, name)
                } else {
                    stringResource(R.string.family_alert_message_with_story, name, story)
                }
                Text(stringResource(R.string.family_alert_heading), style = MaterialTheme.typography.titleMedium)
                Text(stringResource(R.string.family_alert_lead))
                Text(message, modifier = Modifier.testTag("family_alert"))
                RowButtons(
                    onCopy = { copyText(context, context.getString(R.string.family_alert_clip_label), message) },
                    onShare = { shareText(context, context.getString(R.string.family_alert_share_title), message) },
                )
            }
            case.claims?.let { claims ->
                if (claims.hasAnything()) {
                    Text(stringResource(R.string.claims_heading), style = MaterialTheme.typography.titleMedium)
                    claims.claimedIdentity.known()?.let { Text(stringResource(R.string.claims_identity, it)) }
                    claims.amount.known()?.let { Text(stringResource(R.string.claims_amount, it)) }
                    claims.story.known()?.let { Text(stringResource(R.string.claims_story, it)) }
                    if (claims.redFlags.any { it.known() != null }) {
                        val flags = claims.redFlags.mapNotNull { it.known() }.joinToString(stringResource(R.string.list_separator))
                        Text(stringResource(R.string.claims_red_flags, flags))
                    }
                }
            }
            if (case.parentText.isNotBlank()) {
                Text(stringResource(R.string.case_your_text_heading), style = MaterialTheme.typography.titleMedium)
                Text(case.parentText)
            }
            if (case.timeline.isNotEmpty()) {
                Text(stringResource(R.string.case_timeline_heading), style = MaterialTheme.typography.titleMedium)
                case.timeline.forEach { step -> Text("• " + stringResource(CaseCopy.timelineStep(step))) }
            }
            if (pollError && color == CaseColor.OPEN) {
                ErrorText(com.familyshield.app.ui.common.UiText(R.string.case_update_failed))
            }
        }
    }
}

@Composable
private fun RowButtons(onCopy: () -> Unit, onShare: () -> Unit) {
    Column {
        Button(onClick = onCopy, modifier = Modifier.testTag("alert_copy")) { Text(stringResource(R.string.action_copy)) }
        TextButton(onClick = onShare) { Text(stringResource(R.string.action_share)) }
    }
}

private fun Claims.hasAnything(): Boolean =
    claimedIdentity.known() != null || amount.known() != null || story.known() != null || redFlags.any { it.known() != null }

private fun String?.known(): String? = this?.trim()?.takeIf { it.isNotEmpty() && !it.equals("unknown", ignoreCase = true) }
