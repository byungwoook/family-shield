package com.familyshield.app.ui.common

import android.content.Context
import androidx.annotation.StringRes
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.ui.platform.LocalContext
import com.familyshield.app.R
import com.familyshield.app.data.api.ApiException
import com.familyshield.app.data.api.ErrorCodes

/** A string resource plus its format arguments, resolved in the UI's locale. */
@Immutable
data class UiText(@param:StringRes val res: Int, val args: List<Any> = emptyList()) {
    fun resolve(context: Context): String = context.getString(res, *args.toTypedArray())

    @Composable
    fun resolve(): String = resolve(LocalContext.current)

    companion object {
        fun of(@StringRes res: Int, vararg args: Any) = UiText(res, args.toList())
    }
}

/** API failures to the sentence the parent sees. Never shows a raw code or a server body. */
object ErrorMessages {

    fun of(error: Throwable): UiText = UiText(resOf(error))

    @StringRes
    fun resOf(error: Throwable): Int = when (error) {
        is ApiException.Network -> R.string.error_network
        is ApiException.NotConfigured -> R.string.error_not_configured
        is ApiException.Decode -> R.string.error_decode
        is ApiException.Http -> forCode(error.status, error.code)
        else -> R.string.error_generic
    }

    @StringRes
    fun forCode(status: Int, code: String): Int = when (code) {
        ErrorCodes.UNAUTHORIZED -> R.string.error_unauthorized
        ErrorCodes.INVALID_TOKEN -> R.string.error_invalid_token
        ErrorCodes.SIGN_IN_UNAVAILABLE -> R.string.error_sign_in_unavailable
        ErrorCodes.INVALID_BODY -> R.string.error_invalid_body
        ErrorCodes.NOT_FOUND -> R.string.error_not_found
        ErrorCodes.NOT_A_PARENT -> R.string.error_not_a_parent
        ErrorCodes.ALREADY_IN_A_FAMILY -> R.string.error_already_in_a_family
        ErrorCodes.INVITE_NOT_OPEN -> R.string.error_invite_not_open
        ErrorCodes.MEMBER_NOT_PENDING -> R.string.error_member_not_pending
        ErrorCodes.MEMBER_NOT_READY -> R.string.error_member_not_ready
        ErrorCodes.NO_PENDING_NUMBER -> R.string.error_no_pending_number
        ErrorCodes.PHONE_IN_USE -> R.string.error_phone_in_use
        ErrorCodes.INVALID_PHONE -> R.string.error_invalid_phone
        ErrorCodes.UNSUPPORTED_COUNTRY -> R.string.error_unsupported_country
        ErrorCodes.NOT_CALL_ONLY -> R.string.error_not_call_only
        ErrorCodes.OTP_UNAVAILABLE, ErrorCodes.ALLOW_LINK_UNAVAILABLE -> R.string.error_sms_unavailable
        ErrorCodes.SMS_FAILED -> R.string.error_sms_failed
        ErrorCodes.MEMBER_NOT_CALLABLE -> R.string.error_member_not_callable
        ErrorCodes.RATE_LIMITED -> R.string.error_rate_limited
        ErrorCodes.AUDIO_TOO_LARGE -> R.string.error_audio_too_large
        ErrorCodes.UNSUPPORTED_AUDIO -> R.string.error_unsupported_audio
        ErrorCodes.EMPTY_AUDIO -> R.string.error_empty_audio
        ErrorCodes.LENGTH_REQUIRED -> R.string.error_length_required
        ErrorCodes.INVITE_INVALID -> R.string.error_invite_invalid
        ErrorCodes.INVITE_EXPIRED -> R.string.error_invite_expired
        ErrorCodes.NOT_A_CHILD -> R.string.error_not_a_child
        ErrorCodes.BIOMETRIC_REQUIRED -> R.string.error_biometric_required
        ErrorCodes.PHONE_ALREADY_SET -> R.string.error_phone_already_set
        ErrorCodes.SAME_NUMBER -> R.string.error_same_number
        ErrorCodes.OTP_WRONG -> R.string.error_otp_wrong
        ErrorCodes.OTP_EXPIRED -> R.string.error_otp_expired
        ErrorCodes.INVALID_CODE -> R.string.error_invalid_code
        ErrorCodes.NOT_THE_CHILD -> R.string.error_not_the_child
        else -> if (status >= 500) R.string.error_server else R.string.error_generic
    }
}
