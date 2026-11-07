package com.familyshield.app.ui.family

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.familyshield.app.R
import com.familyshield.app.data.FamilyRepository
import com.familyshield.app.data.api.ApiException
import com.familyshield.app.data.api.FamilyCreated
import com.familyshield.app.ui.common.ErrorMessages
import com.familyshield.app.ui.common.ErrorText
import com.familyshield.app.ui.common.UiText
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class CreateFamilyUiState(
    val name: String = "",
    val busy: Boolean = false,
    val error: UiText? = null,
)

class CreateFamilyViewModel(private val families: FamilyRepository) : ViewModel() {
    private val _state = MutableStateFlow(CreateFamilyUiState())
    val state: StateFlow<CreateFamilyUiState> = _state.asStateFlow()

    fun setName(value: String) = _state.update { it.copy(name = value.take(NAME_LIMIT), error = null) }

    fun create(onCreated: (FamilyCreated) -> Unit) {
        val name = _state.value.name.trim()
        if (name.isEmpty()) {
            _state.update { it.copy(error = UiText(R.string.error_name_required)) }
            return
        }
        if (_state.value.busy) return
        _state.update { it.copy(busy = true, error = null) }
        viewModelScope.launch {
            try {
                val family = families.createFamily(name)
                _state.update { it.copy(busy = false) }
                onCreated(family)
            } catch (e: ApiException) {
                _state.update { it.copy(busy = false, error = ErrorMessages.of(e)) }
            }
        }
    }

    companion object {
        const val NAME_LIMIT = 200
    }
}

@Composable
fun CreateFamilyRoute(
    viewModel: CreateFamilyViewModel,
    onCreated: (FamilyCreated) -> Unit,
    onHaveInvite: () -> Unit,
    onSignOut: () -> Unit,
    banner: String? = null,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    CreateFamilyContent(
        state = state,
        onNameChange = viewModel::setName,
        onCreate = { viewModel.create(onCreated) },
        onHaveInvite = onHaveInvite,
        onSignOut = onSignOut,
        banner = banner,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CreateFamilyContent(
    state: CreateFamilyUiState,
    onNameChange: (String) -> Unit,
    onCreate: () -> Unit,
    onHaveInvite: () -> Unit,
    onSignOut: () -> Unit,
    banner: String? = null,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.create_family_title)) },
                actions = { TextButton(onClick = onSignOut) { Text(stringResource(R.string.action_sign_out)) } },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            if (banner != null) {
                Text(banner, modifier = Modifier.testTag("share_waiting"))
            }
            Text(stringResource(R.string.create_family_body), style = MaterialTheme.typography.bodyLarge)
            OutlinedTextField(
                value = state.name,
                onValueChange = onNameChange,
                label = { Text(stringResource(R.string.create_family_name_label)) },
                singleLine = true,
                keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Words),
                modifier = Modifier.fillMaxWidth().testTag("family_name"),
            )
            Button(
                onClick = onCreate,
                enabled = !state.busy,
                modifier = Modifier.fillMaxWidth().testTag("create_family"),
            ) { Text(stringResource(R.string.create_family_button)) }
            TextButton(onClick = onHaveInvite, modifier = Modifier.testTag("have_invite")) {
                Text(stringResource(R.string.have_invite))
            }
            Text(stringResource(R.string.have_invite_hint), style = MaterialTheme.typography.bodyMedium)
            state.error?.let { ErrorText(it) }
        }
    }
}
