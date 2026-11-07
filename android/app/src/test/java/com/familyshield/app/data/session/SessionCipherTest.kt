package com.familyshield.app.data.session

import android.content.Context
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config
import javax.crypto.KeyGenerator

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])
class SessionCipherTest {
    @Test
    fun tokenRoundTripsAndThePreferencesHoldOnlyCiphertext() {
        val key = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()
        val cipher = AesGcmTokenCipher { key }
        val prefs = RuntimeEnvironment.getApplication().getSharedPreferences("session", Context.MODE_PRIVATE)
        val store = EncryptedTokenStore(prefs, cipher)
        store.save("session-token")
        val stored = prefs.getString(EncryptedTokenStore.KEY_CIPHERTEXT, "").orEmpty()
        assertFalse(stored.contains("session-token"))
        assertEquals("session-token", store.load())
        prefs.edit().putString(EncryptedTokenStore.KEY_CIPHERTEXT, "AAAA").commit()
        assertNull(store.load())
        store.clear()
        assertNull(prefs.getString(EncryptedTokenStore.KEY_IV, null))
    }
}
