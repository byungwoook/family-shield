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

@Composable
fun CaseContent(case: ParentCase, pollError: Boolean, onBack: () -> Unit, now: java.time.Instant = java.time.Instant.now()) {
    val color = CaseColor.of(case.color, case.decidedAt)
    if (color == CaseColor.GREEN || color == CaseColor.RED) {
        ResultScreen(case, color, onBack, now)
    } else if (color == CaseColor.OPEN) {
        ProgressScreen(case, pollError, onBack, now)
    } else {
        YellowScreen(case, onBack)
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
