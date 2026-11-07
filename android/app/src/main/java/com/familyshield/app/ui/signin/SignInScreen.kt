package com.familyshield.app.ui.signin

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.familyshield.app.R
import com.familyshield.app.data.AuthRepository
import com.familyshield.app.data.api.ApiException
import com.familyshield.app.domain.ApiLocale
import com.familyshield.app.ui.common.ErrorMessages
import com.familyshield.app.ui.common.ErrorText
import com.familyshield.app.ui.common.UiText
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SignInUiState(
    val devName: String = "",
    val busy: Boolean = false,
    val error: UiText? = null,
)

class SignInViewModel(private val auth: AuthRepository) : ViewModel() {
    private val _state = MutableStateFlow(SignInUiState())
    val state: StateFlow<SignInUiState> = _state.asStateFlow()

    fun setDevName(value: String) = _state.update { it.copy(devName = value.take(AuthRepository.NAME_LIMIT), error = null) }

    fun devSignIn(locale: String) {
        val name = _state.value.devName.trim()
        if (name.isEmpty()) {
            _state.update { it.copy(error = UiText(R.string.error_name_required)) }
            return
        }
        launchSignIn { auth.devSignIn(name, locale) }
    }

    /**
     * A fresh nonce, then Credential Manager with its hash, then our server with
     * the raw value. [requestIdToken] is the activity-bound Google call.
     */
    fun googleSignIn(locale: String, requestIdToken: suspend (hashedNonce: String) -> GoogleIdentity) {
        launchSignIn {
            val nonce = auth.newNonce()
            val identity = requestIdToken(nonce.hashed)
            auth.signInWithGoogle(identity.idToken, nonce, locale, identity.displayName)
        }
    }

    private fun launchSignIn(block: suspend () -> Unit) {
        if (_state.value.busy) return
        _state.update { it.copy(busy = true, error = null) }
        viewModelScope.launch {
            val error: UiText? = try {
                block()
                null
            } catch (e: GoogleSignInError) {
                when (e.kind) {
                    GoogleSignInError.Kind.CANCELLED -> null
                    GoogleSignInError.Kind.NO_ACCOUNT -> UiText(R.string.error_google_no_account)
                    GoogleSignInError.Kind.FAILED -> UiText(R.string.error_google_failed)
                }
            } catch (e: ApiException) {
                ErrorMessages.of(e)
            }
            _state.update { it.copy(busy = false, error = error) }
        }
    }
}

@Composable
fun SignInRoute(
    viewModel: SignInViewModel,
    google: GoogleSignInClient,
    showDevLogin: Boolean,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val locale = ApiLocale.of(LocalConfiguration.current.locales[0])
    SignInContent(
        state = state,
        showGoogle = google.isAvailable,
        showDevLogin = showDevLogin,
        onGoogle = { viewModel.googleSignIn(locale) { hashed -> google.requestIdToken(context, hashed) } },
        onDevNameChange = viewModel::setDevName,
        onDevSignIn = { viewModel.devSignIn(locale) },
    )
}

@Composable
fun SignInContent(
    state: SignInUiState,
    showGoogle: Boolean,
    showDevLogin: Boolean,
    onGoogle: () -> Unit,
    onDevNameChange: (String) -> Unit,
    onDevSignIn: () -> Unit,
) {
    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Spacer(Modifier.height(32.dp))
            Text(stringResource(R.string.app_name), style = MaterialTheme.typography.headlineLarge)
            Text(stringResource(R.string.signin_tagline), style = MaterialTheme.typography.bodyLarge)
            Text(stringResource(R.string.signin_promise), style = MaterialTheme.typography.bodyMedium)
            Text(stringResource(R.string.signin_privacy), style = MaterialTheme.typography.bodySmall)
            if (showGoogle) {
                Button(
                    onClick = onGoogle,
                    enabled = !state.busy,
                    modifier = Modifier.fillMaxWidth().testTag("google_sign_in"),
                ) { Text(stringResource(R.string.signin_google)) }
            }
            if (showDevLogin) {
                DevLoginFields(state, onDevNameChange, onDevSignIn)
            }
            if (!showGoogle && !showDevLogin) {
                Text(stringResource(R.string.signin_no_method), color = MaterialTheme.colorScheme.error)
            }
            state.error?.let { ErrorText(it) }
        }
    }
}
