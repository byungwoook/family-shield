package com.familyshield.app.ui.signin

import android.content.Context
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.GetCredentialException
import androidx.credentials.exceptions.NoCredentialException
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException

/** What Credential Manager gave back: the ID token for our server, and the account name. */
class GoogleIdentity(val idToken: String, val displayName: String?)

/** Why there is no Google ID token. [CANCELLED] shows nothing; the others show a sentence. */
class GoogleSignInError(val kind: Kind, cause: Throwable? = null) : Exception(kind.name, cause) {
    enum class Kind { CANCELLED, NO_ACCOUNT, FAILED }
}

/**
 * "Sign in with Google" through Credential Manager. The ID token is requested
 * for [serverClientId] (the backend's GOOGLE_SERVER_CLIENT_ID) with
 * `nonce = sha256_hex(raw)`, so the server can check the token's nonce claim
 * against the raw nonce it issued (contract §3).
 *
 * Not exercised by the JVM tests: it needs Google Play services and an account.
 */
class GoogleSignInClient(private val serverClientId: String) {

    /** No client id in this build: the Google button is hidden. */
    val isAvailable: Boolean get() = serverClientId.isNotBlank()

    suspend fun requestIdToken(activityContext: Context, hashedNonce: String): GoogleIdentity {
        val option = GetSignInWithGoogleOption.Builder(serverClientId)
            .setNonce(hashedNonce)
            .build()
        val request = GetCredentialRequest.Builder().addCredentialOption(option).build()
        val response = try {
            CredentialManager.create(activityContext).getCredential(activityContext, request)
        } catch (e: GetCredentialCancellationException) {
            throw GoogleSignInError(GoogleSignInError.Kind.CANCELLED, e)
        } catch (e: NoCredentialException) {
            throw GoogleSignInError(GoogleSignInError.Kind.NO_ACCOUNT, e)
        } catch (e: GetCredentialException) {
            throw GoogleSignInError(GoogleSignInError.Kind.FAILED, e)
        }
        val credential = response.credential
        if (credential !is CustomCredential ||
            credential.type != GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL
        ) {
            throw GoogleSignInError(GoogleSignInError.Kind.FAILED)
        }
        val google = try {
            GoogleIdTokenCredential.createFrom(credential.data)
        } catch (e: GoogleIdTokenParsingException) {
            throw GoogleSignInError(GoogleSignInError.Kind.FAILED, e)
        }
        return GoogleIdentity(idToken = google.idToken, displayName = google.displayName)
    }
}
