package com.familyshield.app.data.api

import com.familyshield.app.data.api.ApiClient.Decision
import com.familyshield.app.domain.VoiceNotes
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Assert.assertNotNull
import org.junit.Test
import java.io.File
import java.io.RandomAccessFile

class ApiClientTest {
    private val server = MockWebServer()
    private val seen = mutableListOf<RecordedRequest>()
    private var token: String? = "session-token"
    private var signedOut: String? = null
    private lateinit var client: ApiClient

    @Before
    fun setUp() {
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                seen += request
                return answer(request)
            }
        }
        server.start()
        client = ApiClient(
            baseUrl = server.url("/").toString(),
            tokens = { token },
            onUnauthorized = { signedOut = it },
        )
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun authenticatedCallSendsBearerAndIgnoresUnknownFields() = runTest {
        val me = client.me()
        val request = seen.single()
        assertEquals("GET", request.method)
        assertEquals("/v1/me", request.path)
        assertEquals("Bearer session-token", request.getHeader("Authorization"))
        assertEquals("user-1", me.userId)
        assertEquals("Ada", me.displayName)
        assertEquals(1, me.memberships.size)
        assertNull(signedOut)
    }

    @Test
    fun httpErrorMapsTheErrorCodeAnd401SignsOut() = runTest {
        token = "stale"
        val error = runCatching { client.me() }.exceptionOrNull()
        assertTrue(error is ApiException.Http)
        val http = error as ApiException.Http
        assertEquals(401, http.status)
        assertEquals("unauthorized", http.code)
        assertEquals("stale", signedOut)
    }

    @Test
    fun memberNotCallableAndRateLimitedStayErrors() = runTest {
        val notCallable = runCatching { client.openCase("child-1", "hello") }.exceptionOrNull() as ApiException.Http
        assertEquals(400, notCallable.status)
        assertEquals(ErrorCodes.MEMBER_NOT_CALLABLE, notCallable.code)
        val limited = runCatching { client.openCase("child-2", "hello") }.exceptionOrNull() as ApiException.Http
        assertEquals(429, limited.status)
        assertEquals(ErrorCodes.RATE_LIMITED, limited.code)
        assertNull(signedOut)
    }

    @Test
    fun googleSignInPostsTheRawNonceNotTheHash() = runTest {
        val session = client.signInWithGoogle(
            GoogleSignInRequest(idToken = "id-token", nonce = "raw-nonce", locale = "ko", displayName = "민지"),
        )
        val body = seen.single().body.readUtf8()
        assertTrue(body.contains("\"nonce\":\"raw-nonce\""))
        assertFalse(body.contains("sha256"))
        assertEquals("token-1", session.token)
        assertNull(seen.single().getHeader("Authorization"))
    }

    @Test
    fun pushTokenOmitsEnvForFcm() = runTest {
        val registered = client.registerPushToken(
            PushTokenRequest(provider = "fcm", token = "fcm-token", env = null, locale = "ko"),
        )
        val body = seen.single().body.readUtf8()
        assertEquals("/v1/me/push-token", seen.single().path)
        assertTrue(body.contains("\"provider\":\"fcm\""))
        assertTrue(body.contains("\"token\":\"fcm-token\""))
        assertTrue(body.contains("\"locale\":\"ko\""))
        assertFalse(body.contains("env"))
        assertEquals("registered", registered.status)
    }

    @Test
    fun parsesParentCaseRosterAndCaseList() = runTest {
        val roster = client.members("fam-1")
        assertEquals("child-1", roster.members.single().id)
        assertEquals("0123", roster.members.single().phoneLast4)
        assertTrue(roster.members.single().awaitingConfirm)
        val list = client.familyCases("fam-1", limit = 5)
        assertEquals("/v1/families/fam-1/cases?limit=5", seen.last().path)
        assertEquals("case-1", list.cases.single().id)
        val opened = client.case("case-1")
        assertEquals("yellow", opened.color)
        assertEquals("wrong", opened.result)
        assertEquals("gift_card", opened.patternId)
        assertEquals("start", opened.timeline.first())
        assertEquals("a story", opened.claims?.story)
    }

    @Test
    fun parentActionsUseTheContractPaths() = runTest {
        client.nonce()
        client.createFamily("우리 가족")
        client.addChild("fam-1", "Mina")
        client.reissueInvite("fam-1", "child-1")
        client.confirmMember("fam-1", "child-1", Decision.CONFIRM)
        client.decidePhoneChange("fam-1", "child-1", Decision.REJECT)
        client.addCallOnly("fam-1", "child-1", "+821012345678")
        client.sendAllowLink("fam-1", "child-1")
        client.devLogin(DevLoginRequest(displayName = "Ada", locale = "en"))
        val paths = seen.map { it.path }
        assertEquals("/v1/auth/nonce", paths[0])
        assertEquals("/v1/families", paths[1])
        assertEquals("/v1/families/fam-1/children", paths[2])
        assertEquals("/v1/families/fam-1/members/child-1/invite", paths[3])
        assertEquals("/v1/families/fam-1/members/child-1/confirm", paths[4])
        assertEquals("/v1/families/fam-1/members/child-1/phone-change", paths[5])
        assertEquals("/v1/families/fam-1/members/child-1/call-only", paths[6])
        assertEquals("/v1/families/fam-1/members/child-1/allow-link", paths[7])
        assertEquals("/v1/dev/login", paths[8])
        assertTrue(seen[4].body.readUtf8().contains("\"decision\":\"confirm\""))
        assertTrue(seen[5].body.readUtf8().contains("\"decision\":\"reject\""))
    }

    @Test
    fun voiceNoteIsMultipartWithContentLengthAndJsonStaysJson() = runTest {
        val file = File.createTempFile("voice", ".m4a").apply { writeBytes(byteArrayOf(0, 1, 2, 70, 83)) }
        val opened = client.openCase("child-3", "용돈", CaseAudio(file, "voice.m4a", "audio/mp4"))
        assertEquals("case-9", opened.id)
        val request = seen.single()
        assertEquals("POST", request.method)
        assertTrue(request.getHeader("Content-Type")!!.startsWith("multipart/form-data"))
        val length = request.getHeader("Content-Length")
        assertNotNull(length)
        assertTrue(length!!.all { it.isDigit() })
        assertEquals(request.bodySize, length.toLong())
        assertEquals(null, request.getHeader("Transfer-Encoding"))
        val body = request.body.snapshot().utf8()
        assertTrue(body.contains("name=\"child_member_id\""))
        assertTrue(body.contains("child-3"))
        assertTrue(body.contains("name=\"text\""))
        assertTrue(body.contains("용돈"))
        assertTrue(body.contains("name=\"audio\""))
        assertTrue(body.contains("filename=\"voice.m4a\""))
        assertTrue(body.contains("Content-Type: audio/mp4"))
        assertTrue(request.body.snapshot().utf8().contains("FS") || body.contains("FS"))

        seen.clear()
        client.openCase("child-3", "plain")
        val json = seen.single()
        assertTrue(json.getHeader("Content-Type")!!.startsWith("application/json"))
        assertFalse(json.body.snapshot().utf8().contains("filename="))
        file.delete()
    }

    @Test
    fun aVoiceNoteOverTheLimitIsRefusedBeforeTheRequest() = runTest {
        val big = File.createTempFile("big", ".m4a")
        RandomAccessFile(big, "rw").use { it.setLength(VoiceNotes.MAX_BYTES + 1) }
        val error = runCatching {
            client.openCase("child-3", "", CaseAudio(big, "big.m4a", "audio/mp4"))
        }.exceptionOrNull() as ApiException.Http
        assertEquals(413, error.status)
        assertEquals(ErrorCodes.AUDIO_TOO_LARGE, error.code)
        assertTrue(seen.isEmpty())
        val empty = File.createTempFile("empty", ".aac")
        val emptyError = runCatching {
            client.openCase("child-3", "", CaseAudio(empty, "e.aac", "audio/aac"))
        }.exceptionOrNull() as ApiException.Http
        assertEquals(ErrorCodes.EMPTY_AUDIO, emptyError.code)
        val badType = File.createTempFile("clip", ".mp4").apply { writeBytes(byteArrayOf(1)) }
        val typeError = runCatching {
            client.openCase("child-3", "", CaseAudio(badType, "clip.mp4", "video/mp4"))
        }.exceptionOrNull() as ApiException.Http
        assertEquals(415, typeError.status)
        assertEquals(ErrorCodes.UNSUPPORTED_AUDIO, typeError.code)
        assertTrue(seen.isEmpty())
        big.delete()
        empty.delete()
        badType.delete()
    }

    @Test
    fun blankBaseIsNotConfigured() = runTest {
        val unconfigured = ApiClient("", { "t" })
        val error = runCatching { unconfigured.me() }.exceptionOrNull()
        assertTrue(error is ApiException.NotConfigured)
    }

    private fun answer(request: RecordedRequest): MockResponse {
        val path = request.path.orEmpty()
        val raw = request.body.snapshot().utf8()
        if (path == "/v1/me" && token == "stale") {
            return json(401, """{"error":"unauthorized"}""")
        }
        if (path == "/v1/cases" && raw.contains("child-1")) {
            return json(400, """{"error":"member_not_callable"}""")
        }
        if (path == "/v1/cases" && raw.contains("child-2")) {
            return json(429, """{"error":"rate_limited","extra":"ignored"}""")
        }
        if (path == "/v1/cases" && request.method == "POST") {
            return json(201, """{"id":"case-9","family_id":"fam-1","child_member_id":"child-3","child_display_name":"Mina","state":"calling","result":null,"color":"open","parent_text":"","transcript":null,"claims":null,"pattern_id":null,"timeline":["start"],"created_at":"2026-11-07T00:00:00+00:00","updated_at":"2026-11-07T00:00:00+00:00","decided_at":null}""")
        }
        val ok = when {
            path == "/v1/me" -> """{"user_id":"user-1","display_name":"Ada","locale":"en","memberships":[{"member_id":"m1","family_id":"fam-1","family_name":"Lee","role":"parent","status":"active","display_name":"Ada","extra":1}],"extra":true}"""
            path == "/v1/auth/nonce" -> """{"nonce":"raw-nonce-value","expires_at":"2026-11-07T00:10:00+00:00"}"""
            path == "/v1/auth/google" -> """{"token":"token-1","user_id":"user-1"}"""
            path == "/v1/dev/login" -> """{"token":"token-1","user_id":"user-1","auth_subject":"dev-1"}"""
            path == "/v1/families" -> """{"id":"fam-1","name":"Lee"}"""
            path == "/v1/families/fam-1/children" -> """{"id":"child-1","display_name":"Mina","status":"invited","invite_secret":"ABCD-EFGH-JKLM","invite_expires_at":"2026-11-08T00:00:00+00:00"}"""
            path == "/v1/families/fam-1/members/child-1/invite" -> """{"id":"child-1","invite_secret":"NEW1-NEW2-NEW3","invite_expires_at":"2026-11-08T00:00:00+00:00"}"""
            path == "/v1/families/fam-1/members" -> """{"family_id":"fam-1","members":[{"id":"child-1","role":"child","display_name":"Mina","status":"invited","linked":true,"phone_last4":"0123","awaiting_confirm":true,"phone_verified":true}]}"""
            path.startsWith("/v1/families/fam-1/cases") -> """{"family_id":"fam-1","cases":[{"id":"case-1","child_member_id":"child-1","child_display_name":"Mina","state":"not_confirmed","result":"wrong","color":"yellow","created_at":"2026-11-07T00:00:00+00:00","decided_at":"2026-11-07T00:01:00+00:00"}]}"""
            path == "/v1/families/fam-1/members/child-1/confirm" -> """{"id":"child-1","status":"active","phone_last4":"0123"}"""
            path == "/v1/families/fam-1/members/child-1/phone-change" -> """{"id":"child-1","status":"kept"}"""
            path == "/v1/families/fam-1/members/child-1/call-only" -> """{"status":"link_sent","phone_last4":"5678"}"""
            path == "/v1/families/fam-1/members/child-1/allow-link" -> """{"status":"link_sent","phone_last4":"5678"}"""
            path == "/v1/me/push-token" -> """{"status":"registered","provider":"fcm"}"""
            path == "/v1/cases/case-1" -> """{"id":"case-1","family_id":"fam-1","child_member_id":"child-1","child_display_name":"Mina","state":"not_confirmed","result":"wrong","color":"yellow","parent_text":"send money","transcript":null,"claims":{"claimed_identity":"unknown","amount":"$50","story":"a story","red_flags":["gift card"]},"pattern_id":"gift_card","timeline":["start","static_code_mismatch"],"created_at":"2026-11-07T00:00:00+00:00","updated_at":"2026-11-07T00:01:00+00:00","decided_at":"2026-11-07T00:01:00+00:00","future_field":1}"""
            else -> return json(500, """{"error":"unavailable"}""")
        }
        return json(if (path == "/v1/auth/nonce" || path == "/v1/dev/login" || path.endsWith("/children") || path.endsWith("/invite") || path == "/v1/families") 201 else if (path.endsWith("call-only") || path.endsWith("allow-link")) 202 else 200, ok)
    }

    private fun json(code: Int, body: String) = MockResponse()
        .setResponseCode(code)
        .setHeader("Content-Type", "application/json")
        .setBody(body)
}
