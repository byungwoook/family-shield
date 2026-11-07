package com.familyshield.app.ui.signin

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import com.familyshield.app.R

/** Debug builds only. The release source set has an empty version of this function. */
@Composable
fun DevLoginFields(
    state: SignInUiState,
    onDevNameChange: (String) -> Unit,
    onDevSignIn: () -> Unit,
) {
    Column {
        HorizontalDivider()
        Text(stringResource(R.string.signin_dev_heading), style = MaterialTheme.typography.titleSmall)
        OutlinedTextField(
            value = state.devName,
            onValueChange = onDevNameChange,
            label = { Text(stringResource(R.string.signin_dev_name_label)) },
            singleLine = true,
            keyboardOptions = KeyboardOptions(
                capitalization = KeyboardCapitalization.Words,
                imeAction = ImeAction.Done,
            ),
            modifier = Modifier.fillMaxWidth().testTag("dev_name"),
        )
        OutlinedButton(
            onClick = onDevSignIn,
            enabled = !state.busy,
            modifier = Modifier.fillMaxWidth().testTag("dev_sign_in"),
        ) { Text(stringResource(R.string.signin_dev_button)) }
    }
}
