package com.familyshield.app.ui

import android.app.Activity
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.familyshield.app.AppContainer
import com.familyshield.app.data.api.ApiException
import com.familyshield.app.R
import com.familyshield.app.data.api.ParentCase
import com.familyshield.app.domain.ApiLocale
import com.familyshield.app.ui.caseflow.CaseRoute
import com.familyshield.app.ui.caseflow.CaseViewModel
import com.familyshield.app.ui.child.AcceptInviteContent
import com.familyshield.app.ui.child.AcceptInviteViewModel
import com.familyshield.app.ui.child.ChildRoute
import com.familyshield.app.ui.child.ChildViewModel
import com.familyshield.app.ui.common.FailureBox
import com.familyshield.app.ui.common.LoadingBox
import com.familyshield.app.ui.family.CreateFamilyRoute
import com.familyshield.app.ui.family.CreateFamilyViewModel
import com.familyshield.app.ui.family.DraftAudio
import com.familyshield.app.ui.family.FamilyRoute
import com.familyshield.app.ui.family.FamilyViewModel
import com.familyshield.app.ui.signin.SignInRoute
import com.familyshield.app.ui.signin.SignInViewModel

@Composable
fun AppRoot(container: AppContainer) {
    val rootViewModel = viewModel {
        RootViewModel(container.session, container.auth, container.cases)
    }
    val state by rootViewModel.state.collectAsStateWithLifecycle()
    val locale = ApiLocale.of(LocalConfiguration.current.locales[0])
    val sessionToken by container.session.token.collectAsStateWithLifecycle()
    LaunchedEffect(sessionToken, locale) {
        if (sessionToken != null) {
            try {
                container.push.register(locale)
            } catch (_: ApiException) {
                // A failed registration must not block the parent. No token is logged.
            }
        }
    }
    var openCaseId by rememberSaveable { mutableStateOf<String?>(null) }
    val caseId = openCaseId
    if (caseId != null && state is RootState.Parent) {
        val caseViewModel = viewModel(key = "case-$caseId") {
            CaseViewModel(container.cases, caseId, container.cases.cached(caseId))
        }
        CaseRoute(caseViewModel, onBack = { openCaseId = null })
        return
    }
    when (val current = state) {
        RootState.Loading -> LoadingBox()
        RootState.SignedOut -> {
            if (LocalContext.current !is Activity) return
            val signIn = viewModel { SignInViewModel(container.auth) }
            val waiting by container.shares.pending.collectAsStateWithLifecycle()
            SignInRoute(
                signIn,
                container.google,
                showDevLogin = container.devLogin,
                banner = if (waiting != null) stringResource(R.string.share_waiting_signin) else null,
            )
        }
        RootState.NeedsFamily -> {
            var joining by rememberSaveable { mutableStateOf(false) }
            val waiting by container.shares.pending.collectAsStateWithLifecycle()
            if (joining) {
                val invite = viewModel { AcceptInviteViewModel(container.child) }
                val inviteState by invite.state.collectAsStateWithLifecycle()
                AcceptInviteContent(
                    state = inviteState,
                    onSecret = invite::setSecret,
                    onAccept = { invite.accept { rootViewModel.retry() } },
                    onBack = { joining = false },
                )
            } else {
                val create = viewModel { CreateFamilyViewModel(container.families) }
                CreateFamilyRoute(
                    create,
                    onCreated = rootViewModel::familyCreated,
                    onHaveInvite = { joining = true },
                    onSignOut = {
                        container.shares.discardPending()
                        rootViewModel.signOut()
                    },
                    banner = if (waiting != null) stringResource(R.string.share_waiting_family) else null,
                )
            }
        }
        is RootState.Parent -> {
            val family = viewModel(key = "family-${current.familyId}") {
                FamilyViewModel(
                    current.familyId,
                    container.families,
                    container.cases,
                    deleteDraft = container.shares::delete,
                )
            }
            LaunchedEffect(sessionToken) { family.bindSession(sessionToken) }
            val pending by container.shares.pending.collectAsStateWithLifecycle()
            LaunchedEffect(pending?.token) {
                val share = pending ?: return@LaunchedEffect
                family.applyShare(
                    share.text,
                    share.audio?.let { DraftAudio(it.file, it.displayName, it.contentType) },
                    share.problem,
                    share.token,
                )
                container.shares.consume(share.token)
            }
            FamilyRoute(
                viewModel = family,
                familyName = current.familyName,
                onOpenCase = { opened: ParentCase -> openCaseId = opened.id },
                onOpenRecent = { openCaseId = it },
                onSignOut = {
                    family.discardDraft()
                    container.shares.discardPending()
                    rootViewModel.signOut()
                },
            )
        }
        is RootState.Child -> {
            val childModel = viewModel(key = "child-${current.memberId}-${current.status}") {
                ChildViewModel(
                    memberId = current.memberId,
                    familyName = current.familyName,
                    status = current.status,
                    child = container.child,
                    progress = container.childProgress,
                )
            }
            val generation by container.alerts.generation.collectAsStateWithLifecycle()
            LaunchedEffect(childModel, generation) {
                container.alerts.currentCaseId()?.let { childModel.openAlert(it) }
            }
            val pending by container.shares.pending.collectAsStateWithLifecycle()
            ChildRoute(
                viewModel = childModel,
                biometric = container.biometric,
                onSignOut = {
                    container.shares.discardPending()
                    rootViewModel.signOut()
                },
                onRefreshMembership = rootViewModel::retry,
                shareNotice = if (pending != null) stringResource(R.string.share_needs_parent) else null,
                onDiscardShare = if (pending != null) container.shares::discardPending else null,
            )
        }
        RootState.MembershipPending -> {
            val pending by container.shares.pending.collectAsStateWithLifecycle()
            Placeholder(
                title = stringResource(R.string.membership_pending_title),
                body = stringResource(R.string.membership_pending_body),
                onSignOut = {
                    container.shares.discardPending()
                    rootViewModel.signOut()
                },
                notice = if (pending != null) stringResource(R.string.share_needs_parent) else null,
                onDiscardNotice = if (pending != null) container.shares::discardPending else null,
            )
        }
        is RootState.Failed -> FailureBox(current.message, onRetry = rootViewModel::retry)
    }
}

@Composable
private fun Placeholder(
    title: String,
    body: String,
    onSignOut: () -> Unit,
    notice: String? = null,
    onDiscardNotice: (() -> Unit)? = null,
) {
    Column(
        Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
        horizontalAlignment = Alignment.Start,
    ) {
        Text(title, style = MaterialTheme.typography.headlineSmall)
        Text(body)
        if (notice != null) {
            Text(notice, modifier = Modifier.testTag("share_needs_parent"))
            if (onDiscardNotice != null) {
                TextButton(onClick = onDiscardNotice) { Text(stringResource(R.string.share_discard)) }
            }
        }
        Button(onClick = onSignOut) { Text(stringResource(R.string.action_sign_out)) }
    }
}
