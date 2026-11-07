package com.familyshield.app.data.api

import java.io.IOException

/**
 * Every failure the API client reports. The message never contains a request
 * or response body, a token, or case text, so it is safe to show in a crash log.
 */
sealed class ApiException(message: String, cause: Throwable? = null) : Exception(message, cause) {

    /**
     * The server answered with a non-2xx status. [code] is the `{"error": code}`
     * value, or `http_<status>` when the body had none (framework 404/405 send
     * `{"detail": ...}`, and a proxy may send HTML).
     */
    class Http(val status: Int, val code: String) : ApiException("HTTP $status $code")

    /** No answer: offline, DNS, TLS, timeout, or the connection dropped. */
    class Network(cause: IOException) : ApiException("network: ${cause.javaClass.simpleName}", cause)

    /** A 2xx answer whose body is not the shape the contract promises. */
    class Decode(cause: Throwable) : ApiException("decode: ${cause.javaClass.simpleName}", cause)

    /** This build has no server address (a release built without -PfsApiBase). */
    class NotConfigured : ApiException("no API base URL in this build")

    /** True for the server's `error` code [expected], whatever the status. */
    fun isCode(expected: String): Boolean = this is Http && code == expected
}

/** Error codes from docs/API_CONTRACT.md that the parent screens treat specially. */
object ErrorCodes {
    const val UNAUTHORIZED = "unauthorized"
    const val INVALID_TOKEN = "invalid_token"
    const val INVALID_BODY = "invalid_body"
    const val NOT_FOUND = "not_found"
    const val NOT_A_PARENT = "not_a_parent"
    const val ALREADY_IN_A_FAMILY = "already_in_a_family"
    const val INVITE_NOT_OPEN = "invite_not_open"
    const val MEMBER_NOT_PENDING = "member_not_pending"
    const val MEMBER_NOT_READY = "member_not_ready"
    const val NO_PENDING_NUMBER = "no_pending_number"
    const val PHONE_IN_USE = "phone_in_use"
    const val INVALID_PHONE = "invalid_phone"
    const val UNSUPPORTED_COUNTRY = "unsupported_country"
    const val NOT_CALL_ONLY = "not_call_only"
    const val OTP_UNAVAILABLE = "otp_unavailable"
    const val ALLOW_LINK_UNAVAILABLE = "allow_link_unavailable"
    const val SMS_FAILED = "sms_failed"
    const val MEMBER_NOT_CALLABLE = "member_not_callable"
    const val RATE_LIMITED = "rate_limited"
    const val AUDIO_TOO_LARGE = "audio_too_large"
    const val UNSUPPORTED_AUDIO = "unsupported_audio"
    const val EMPTY_AUDIO = "empty_audio"
    const val LENGTH_REQUIRED = "length_required"
    const val SIGN_IN_UNAVAILABLE = "sign_in_unavailable"
    const val UNAVAILABLE = "unavailable"
    const val CONFIG = "config"
    const val INVITE_INVALID = "invite_invalid"
    const val INVITE_EXPIRED = "invite_expired"
    const val NOT_A_CHILD = "not_a_child"
    const val BIOMETRIC_REQUIRED = "biometric_required"
    const val PHONE_ALREADY_SET = "phone_already_set"
    const val SAME_NUMBER = "same_number"
    const val OTP_WRONG = "otp_wrong"
    const val OTP_EXPIRED = "otp_expired"
    const val INVALID_CODE = "invalid_code"
    const val NOT_THE_CHILD = "not_the_child"
}
