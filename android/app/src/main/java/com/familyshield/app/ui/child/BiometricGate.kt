package com.familyshield.app.ui.child

import android.os.Build
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import com.familyshield.app.R
import com.familyshield.app.domain.AuthenticatorChoice
import com.familyshield.app.domain.BiometricPolicy

/** Why the child is being asked. The prompt title depends on it; the result is only success or cancel. */
enum class BiometricPurpose { ANSWER_YES, ANSWER_NO, REVEAL_CODE, RESET_CODE }

fun interface BiometricGate {
    fun confirm(activity: FragmentActivity, purpose: BiometricPurpose, onResult: (Boolean) -> Unit)
}

/**
 * `BiometricPrompt` with a strong biometric. On API 30+ the same prompt can
 * fall back to the device passcode. Below that, a device that has a strong
 * biometric is not offered the passcode in the same prompt (the platform
 * refuses the combination). A device with no strong biometric gets the
 * passcode, so a child is not locked out of answering.
 */
class AndroidBiometricGate(
    private val sdkInt: Int = Build.VERSION.SDK_INT,
) : BiometricGate {
    override fun confirm(activity: FragmentActivity, purpose: BiometricPurpose, onResult: (Boolean) -> Unit) {
        val strong = BiometricManager.from(activity)
            .canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG) == BiometricManager.BIOMETRIC_SUCCESS
        val choice = BiometricPolicy.choose(sdkInt, strong)
        val prompt = BiometricPrompt(
            activity,
            ContextCompat.getMainExecutor(activity),
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    onResult(true)
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    onResult(false)
                }
            },
        )
        prompt.authenticate(promptInfo(activity, purpose, choice))
    }

    companion object {
        fun promptInfo(
            activity: FragmentActivity,
            purpose: BiometricPurpose,
            choice: AuthenticatorChoice,
        ): BiometricPrompt.PromptInfo {
            val title = when (purpose) {
                BiometricPurpose.ANSWER_YES, BiometricPurpose.ANSWER_NO -> R.string.biometric_title_answer
                BiometricPurpose.REVEAL_CODE -> R.string.biometric_title_code
                BiometricPurpose.RESET_CODE -> R.string.biometric_title_reset
            }
            val builder = BiometricPrompt.PromptInfo.Builder()
                .setTitle(activity.getString(title))
                .setSubtitle(activity.getString(R.string.biometric_subtitle))
            when (choice) {
                AuthenticatorChoice.STRONG -> builder
                    .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG)
                    .setNegativeButtonText(activity.getString(R.string.action_cancel))
                AuthenticatorChoice.STRONG_OR_DEVICE -> builder.setAllowedAuthenticators(
                    BiometricManager.Authenticators.BIOMETRIC_STRONG or BiometricManager.Authenticators.DEVICE_CREDENTIAL,
                )
                AuthenticatorChoice.DEVICE_ONLY -> if (Build.VERSION.SDK_INT >= 30) {
                    builder.setAllowedAuthenticators(BiometricManager.Authenticators.DEVICE_CREDENTIAL)
                } else {
                    @Suppress("DEPRECATION")
                    builder.setDeviceCredentialAllowed(true)
                }
            }
            return builder.build()
        }
    }
}
