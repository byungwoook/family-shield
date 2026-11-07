package com.familyshield.app.data

import com.familyshield.app.data.api.ApiClient
import com.familyshield.app.data.api.PushTokenRequest

/** A device FCM token, or null when this build has no Firebase project. */
fun interface PushTokenSource {
    suspend fun current(): String?
}

/**
 * Registers the parent's FCM token (`POST /v1/me/push-token`) so number-change
 * notices can reach this device. `env` stays null: the contract requires that
 * for `provider = fcm`. A missing token (no `google-services.json` in this
 * build) is a no-op, not an error.
 */
class PushRegistrar(
    private val api: PushApi,
    private val tokens: PushTokenSource,
) {
    suspend fun register(locale: String) {
        val token = tokens.current()?.trim().orEmpty()
        if (token.isEmpty()) return
        api.register(
            PushTokenRequest(
                provider = "fcm",
                token = token,
                env = null,
                locale = locale,
            ),
        )
    }
}

fun interface PushApi {
    suspend fun register(body: PushTokenRequest)
}

class ApiPushApi(private val api: ApiClient) : PushApi {
    override suspend fun register(body: PushTokenRequest) {
        api.registerPushToken(body)
    }
}

/** This build does not ship a Firebase config, so there is no device token. */
object NoFirebaseToken : PushTokenSource {
    override suspend fun current(): String? = null
}
