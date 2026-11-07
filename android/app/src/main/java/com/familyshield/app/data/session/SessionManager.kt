package com.familyshield.app.data.session

import android.content.SharedPreferences
import com.familyshield.app.data.api.TokenSource
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.Base64

/** Where the session token lives between launches. */
interface TokenStore {
    fun load(): String?
    fun save(token: String)
    fun clear()
}

/**
 * The token encrypted with [cipher] (an Android Keystore AES-GCM key in the
 * app). The preferences file holds only the IV and the ciphertext, base64.
 * A value that no longer opens (key reset, restored backup, tampering) is
 * dropped and reads as signed out.
 */
class EncryptedTokenStore(
    private val prefs: SharedPreferences,
    private val cipher: TokenCipher,
) : TokenStore {

    override fun load(): String? {
        val iv = prefs.getString(KEY_IV, null) ?: return null
        val ciphertext = prefs.getString(KEY_CIPHERTEXT, null) ?: return null
        return try {
            val plain = cipher.open(SealedValue(DECODER.decode(iv), DECODER.decode(ciphertext)))
            String(plain, Charsets.UTF_8).takeIf { it.isNotBlank() }
        } catch (e: Exception) {
            // GeneralSecurityException, a bad base64 value, or a Keystore provider error.
            clear()
            null
        }
    }

    override fun save(token: String) {
        val sealed = cipher.seal(token.toByteArray(Charsets.UTF_8))
        prefs.edit()
            .putString(KEY_IV, ENCODER.encodeToString(sealed.iv))
            .putString(KEY_CIPHERTEXT, ENCODER.encodeToString(sealed.ciphertext))
            .commit()
    }

    override fun clear() {
        prefs.edit().remove(KEY_IV).remove(KEY_CIPHERTEXT).commit()
    }

    companion object {
        const val PREFS_NAME = "family_shield_session"
        const val KEY_IV = "session_iv"
        const val KEY_CIPHERTEXT = "session_ciphertext"
        private val ENCODER = Base64.getEncoder()
        private val DECODER = Base64.getDecoder()
    }
}

/**
 * The signed-in state. [token] is null while signed out. The API client reads
 * the token from here and calls [signOutIfCurrent] on a 401, so an expired or
 * revoked session from any screen lands the app on sign-in.
 */
class SessionManager(private val store: TokenStore) : TokenSource {
    private val lock = Any()
    private val _token = MutableStateFlow<String?>(null)
    private val _loaded = MutableStateFlow(false)

    val token: StateFlow<String?> = _token.asStateFlow()

    /** False until [load] read the stored token (or found none). */
    val loaded: StateFlow<Boolean> = _loaded.asStateFlow()

    /** Reads the stored token. Call off the main thread: it touches the Keystore. */
    fun load() {
        synchronized(lock) {
            if (_loaded.value) return
            _token.value = store.load()
            _loaded.value = true
        }
    }

    override fun currentToken(): String? = _token.value

    fun signIn(token: String) {
        synchronized(lock) {
            store.save(token)
            _token.value = token
            _loaded.value = true
        }
    }

    fun signOut() {
        synchronized(lock) {
            store.clear()
            _token.value = null
            _loaded.value = true
        }
    }

    /** A 401 for [rejected]. Ignored when a newer sign-in already replaced that token. */
    fun signOutIfCurrent(rejected: String) {
        synchronized(lock) {
            if (_token.value == rejected) signOut()
        }
    }
}
