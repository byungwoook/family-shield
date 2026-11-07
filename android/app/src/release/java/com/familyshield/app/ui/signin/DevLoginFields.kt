package com.familyshield.app.ui.signin

import androidx.compose.runtime.Composable

/** Release builds have no developer sign-in. */
@Suppress("UNUSED_PARAMETER")
@Composable
fun DevLoginFields(
    state: SignInUiState,
    onDevNameChange: (String) -> Unit,
    onDevSignIn: () -> Unit,
) = Unit
