package com.familyshield.app.data.api

import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.serialization.DeserializationStrategy
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlinx.serialization.serializer
import okhttp3.Call
import okhttp3.Callback
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import com.familyshield.app.domain.VoiceNotes
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import java.io.IOException
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/** One JSON configuration for every request and response. */
val ApiJson: Json = Json {
    // The server may add response fields; an old app must keep working.
    ignoreUnknownKeys = true
    // Null request fields are left out (every nullable request field has a server default).
    explicitNulls = false
    encodeDefaults = true
}

/** Where the client reads the current session token. Null or blank: signed out. */
fun interface TokenSource {
    fun currentToken(): String?
}

/**
 * The only HTTP client of the app. One suspend function per route in
 * docs/API_CONTRACT.md. It adds `Authorization: Bearer <token>`, maps
 * `{"error": code}` bodies to [ApiException.Http], and calls [onUnauthorized]
 * with the rejected token when an authenticated call answers 401, so the
 * session layer can sign out.
 *
 * Nothing here logs. There is no logging interceptor on purpose: request and
 * response bodies carry case text, names, invite secrets, and session tokens.
 */
class ApiClient(
    baseUrl: String,
    private val tokens: TokenSource,
    private val onUnauthorized: (rejectedToken: String) -> Unit = {},
    private val http: OkHttpClient = defaultHttpClient(),
) {
    private val base: HttpUrl? = baseUrl.trim().takeIf { it.isNotEmpty() }?.toHttpUrlOrNull()

    /** False when this build has no usable server address. */
    val isConfigured: Boolean get() = base != null

    // ---------- Auth ----------

    suspend fun nonce(): NonceResponse =
        postEmpty(url("v1", "auth", "nonce"), auth = false)

    suspend fun signInWithGoogle(body: GoogleSignInRequest): SessionResponse =
        post(url("v1", "auth", "google"), body, auth = false)

    suspend fun devLogin(body: DevLoginRequest): DevLoginResponse =
        post(url("v1", "dev", "login"), body, auth = false)

    // ---------- Me ----------

    suspend fun me(): Me = get(url("v1", "me"))

    // ---------- Family (parent) ----------

    suspend fun createFamily(name: String): FamilyCreated =
        post(url("v1", "families"), CreateFamilyRequest(name))

    suspend fun addChild(familyId: String, displayName: String): ChildInvite =
        post(url("v1", "families", familyId, "children"), AddChildRequest(displayName))

    suspend fun members(familyId: String): Roster =
        get(url("v1", "families", familyId, "members"))

    suspend fun familyCases(familyId: String, limit: Int = 20): CaseList =
        get(url("v1", "families", familyId, "cases") { addQueryParameter("limit", limit.toString()) })

    suspend fun reissueInvite(familyId: String, memberId: String): InviteReissued =
        postEmpty(url("v1", "families", familyId, "members", memberId, "invite"))

    suspend fun confirmMember(familyId: String, memberId: String, decision: Decision): MemberDecision =
        post(url("v1", "families", familyId, "members", memberId, "confirm"), DecisionRequest(decision.wire))

    suspend fun decidePhoneChange(familyId: String, memberId: String, decision: Decision): PhoneChangeDecision =
        post(url("v1", "families", familyId, "members", memberId, "phone-change"), DecisionRequest(decision.wire))

    suspend fun addCallOnly(familyId: String, memberId: String, phoneE164: String): LinkSent =
        post(url("v1", "families", familyId, "members", memberId, "call-only"), PhoneRequest(phoneE164))

    suspend fun sendAllowLink(familyId: String, memberId: String): LinkSent =
        postEmpty(url("v1", "families", familyId, "members", memberId, "allow-link"))

    // ---------- Cases (parent) ----------

    /**
     * Opens a case. With [audio], the body is multipart (`child_member_id`,
     * `text`, file `audio`) and `Content-Length` is set because every part has
     * a known length. Without [audio], the body stays JSON. Either way this is
     * the call the parent makes by tapping Verify, not by sharing.
     */
    suspend fun openCase(childMemberId: String, text: String, audio: CaseAudio? = null): ParentCase {
        if (audio == null) {
            return post(url("v1", "cases"), CreateCaseRequest(childMemberId, text))
        }
        rejectUnusable(audio)
        val multipart = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("child_member_id", childMemberId)
            .addFormDataPart("text", text)
            .addFormDataPart(
                "audio",
                VoiceNotes.uploadName(audio.uploadName, audio.contentType),
                audio.file.asRequestBody(audio.contentType.toMediaType()),
            )
            .build()
        // MultipartBody.contentLength() is the exact byte count. OkHttp then
        // sends Content-Length instead of chunked transfer. The server rejects
        // a multipart case that has no numeric Content-Length (411).
        check(multipart.contentLength() >= 0L)
        val upload = http.newBuilder()
            .writeTimeout(2, TimeUnit.MINUTES)
            .readTimeout(30, TimeUnit.SECONDS)
            .callTimeout(2, TimeUnit.MINUTES)
            .build()
        return execute(
            url("v1", "cases"),
            method = "POST",
            body = multipart,
            decoder = serializer<ParentCase>(),
            auth = true,
            client = upload,
        )
    }

    suspend fun case(caseId: String): ParentCase = get(url("v1", "cases", caseId))

    // ---------- Child side (the child path is milestone 14; parsed here so the contract is covered) ----------

    suspend fun acceptInvite(secret: String): InviteAccepted =
        post(url("v1", "invites", "accept"), AcceptInviteRequest(secret))

    suspend fun startOtp(body: OtpStartRequest): OtpStarted = post(url("v1", "phones", "otp"), body)

    suspend fun checkOtp(body: OtpCheckRequest): OtpChecked = post(url("v1", "phones", "otp", "check"), body)

    suspend fun setCheckCode(body: CheckCodeRequest): StatusResponse = post(url("v1", "me", "check-code"), body)

    suspend fun registerPushToken(body: PushTokenRequest): PushTokenRegistered =
        post(url("v1", "me", "push-token"), body)

    suspend fun childCase(caseId: String): ChildCase = get(url("v1", "cases", caseId))

    suspend fun answerCase(caseId: String, answer: String): ChildCase =
        post(url("v1", "cases", caseId, "answer"), AnswerRequest(answer))

    suspend fun callCode(caseId: String): CallCode = get(url("v1", "cases", caseId, "call-code"))

    // ---------- DEV_AUTH only (a local backend; the e2e test drives outcomes with these) ----------

    suspend fun devActivate(memberId: String, phoneE164: String, userId: String? = null): DevActivated =
        post(url("v1", "dev", "members", memberId, "activate"), DevActivateRequest(phoneE164, userId))

    suspend fun devSetCheckCode(memberId: String, code: String, biometricOk: Boolean = false): StatusResponse =
        post(url("v1", "dev", "members", memberId, "check-code"), CheckCodeRequest(code, biometricOk))

    suspend fun devDigits(caseId: String, digits: String): ParentCase =
        post(url("v1", "dev", "cases", caseId, "digits"), DigitsRequest(digits))

    // ---------- Plumbing ----------

    /** Builds base + segments. Every segment is percent-encoded, so an id can never add a path. */
    private fun url(vararg segments: String, query: HttpUrl.Builder.() -> Unit = {}): HttpUrl? {
        val root = base ?: return null
        return root.newBuilder().apply {
            segments.forEach { addPathSegment(it) }
            query()
        }.build()
    }

    private suspend inline fun <reified Res> get(url: HttpUrl?, auth: Boolean = true): Res =
        execute(url, method = "GET", body = null, decoder = serializer<Res>(), auth = auth)

    private suspend inline fun <reified Req, reified Res> post(url: HttpUrl?, body: Req, auth: Boolean = true): Res =
        execute(
            url,
            method = "POST",
            body = ApiJson.encodeToString(serializer<Req>(), body).toRequestBody(JSON),
            decoder = serializer<Res>(),
            auth = auth,
        )

    /** A POST the contract defines with no body (nonce, invite re-issue, allow link). */
    private suspend inline fun <reified Res> postEmpty(url: HttpUrl?, auth: Boolean = true): Res =
        execute(url, method = "POST", body = ByteArray(0).toRequestBody(null), decoder = serializer<Res>(), auth = auth)

    private suspend fun <T> execute(
        url: HttpUrl?,
        method: String,
        body: RequestBody?,
        decoder: DeserializationStrategy<T>,
        auth: Boolean,
        client: OkHttpClient = http,
    ): T {
        val target = url ?: throw ApiException.NotConfigured()
        val request = Request.Builder()
            .url(target)
            .header("Accept", "application/json")
            .method(method, body)
        val token = if (auth) tokens.currentToken()?.takeIf { it.isNotBlank() } else null
        if (auth) {
            // Signed out: do not send an unauthenticated request the server would refuse anyway.
            token ?: throw ApiException.Http(401, ErrorCodes.UNAUTHORIZED)
            request.header("Authorization", "Bearer $token")
        }
        val raw = try {
            client.newCall(request.build()).await()
        } catch (e: IOException) {
            throw ApiException.Network(e)
        }
        if (raw.status !in 200..299) {
            if (raw.status == 401 && token != null) onUnauthorized(token)
            throw ApiException.Http(raw.status, errorCode(raw.body) ?: "http_${raw.status}")
        }
        return try {
            ApiJson.decodeFromString(decoder, raw.body)
        } catch (e: SerializationException) {
            throw ApiException.Decode(e)
        } catch (e: IllegalArgumentException) {
            throw ApiException.Decode(e)
        }
    }

    private fun errorCode(body: String): String? = try {
        ApiJson.decodeFromString(ErrorBody.serializer(), body).error?.takeIf { it.isNotBlank() }
    } catch (e: SerializationException) {
        null
    } catch (e: IllegalArgumentException) {
        null
    }

    private class RawResponse(val status: Int, val body: String)

    /** Enqueues the call and cancels it when the coroutine is cancelled (a screen that stops polling). */
    private suspend fun Call.await(): RawResponse = suspendCancellableCoroutine { continuation ->
        continuation.invokeOnCancellation { cancel() }
        enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                continuation.resumeWithException(e)
            }

            override fun onResponse(call: Call, response: Response) {
                val raw = try {
                    response.use { RawResponse(it.code, it.body?.string().orEmpty()) }
                } catch (e: IOException) {
                    continuation.resumeWithException(e)
                    return
                }
                continuation.resume(raw)
            }
        })
    }

    /**
     * Refuses a voice note the server would refuse, before any socket is opened.
     * The codes match `POST /v1/cases` so the screen can show the same sentence.
     */
    private fun rejectUnusable(audio: CaseAudio) {
        if (!AUDIO_TYPE.matches(audio.contentType)) {
            throw ApiException.Http(415, ErrorCodes.UNSUPPORTED_AUDIO)
        }
        val length = if (audio.file.isFile) audio.file.length() else -1L
        if (length <= 0L) throw ApiException.Http(400, ErrorCodes.EMPTY_AUDIO)
        if (length > VoiceNotes.MAX_BYTES) throw ApiException.Http(413, ErrorCodes.AUDIO_TOO_LARGE)
    }

    enum class Decision(val wire: String) { CONFIRM("confirm"), REJECT("reject") }

    companion object {
        private val JSON = "application/json; charset=utf-8".toMediaType()
        private val AUDIO_TYPE = Regex("audio/[a-z0-9.+-]+")

        fun defaultHttpClient(): OkHttpClient = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .writeTimeout(20, TimeUnit.SECONDS)
            .callTimeout(30, TimeUnit.SECONDS)
            .build()
    }
}
