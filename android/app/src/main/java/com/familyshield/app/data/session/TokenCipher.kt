package com.familyshield.app.data.session

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Ciphertext plus the GCM IV it was sealed with. Both are safe to store; the key is not here. */
class SealedValue(val iv: ByteArray, val ciphertext: ByteArray)

/** Encrypts the session token at rest. Production: [AesGcmTokenCipher] over an Android Keystore key. */
interface TokenCipher {
    fun seal(plaintext: ByteArray): SealedValue

    /** Throws when the value was not sealed with this key (wrong key, tampered, or key gone). */
    fun open(sealed: SealedValue): ByteArray
}

/**
 * AES-256-GCM with a 128-bit tag. The key comes from [keyProvider]; the
 * cipher picks a fresh random IV for every seal (Android Keystore keys
 * require that), so this exact code runs with a Keystore key on a device
 * and with a software key in JVM tests.
 */
class AesGcmTokenCipher(private val keyProvider: () -> SecretKey) : TokenCipher {

    override fun seal(plaintext: ByteArray): SealedValue {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, keyProvider())
        val ciphertext = cipher.doFinal(plaintext)
        return SealedValue(iv = cipher.iv, ciphertext = ciphertext)
    }

    override fun open(sealed: SealedValue): ByteArray {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, keyProvider(), GCMParameterSpec(TAG_BITS, sealed.iv))
        return cipher.doFinal(sealed.ciphertext)
    }

    companion object {
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val TAG_BITS = 128
    }
}

/**
 * The non-exportable AES key in the Android Keystore. Created on first use.
 * Not reachable from JVM unit tests (Robolectric has no AndroidKeyStore
 * provider); see android/README.md for what is verified where.
 */
object KeystoreKeys {
    private const val PROVIDER = "AndroidKeyStore"
    const val SESSION_KEY_ALIAS = "family_shield_session_key_v1"

    fun sessionCipher(): TokenCipher = AesGcmTokenCipher { getOrCreate(SESSION_KEY_ALIAS) }

    @Synchronized
    fun getOrCreate(alias: String): SecretKey {
        val store = KeyStore.getInstance(PROVIDER).apply { load(null) }
        (store.getKey(alias, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, PROVIDER)
        generator.init(
            KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .setRandomizedEncryptionRequired(true)
                .build(),
        )
        return generator.generateKey()
    }
}
