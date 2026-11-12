package com.familyshield.app.ui

import android.graphics.Bitmap
import androidx.compose.runtime.Composable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.requiredSize
import androidx.compose.ui.Modifier
import android.graphics.Canvas
import androidx.compose.ui.platform.testTag
import androidx.activity.ComponentActivity
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.unit.dp
import com.familyshield.app.data.api.CaseSummary
import com.familyshield.app.data.api.Claims
import com.familyshield.app.sampleCase
import com.familyshield.app.sampleChild
import com.familyshield.app.ui.caseflow.CaseContent
import com.familyshield.app.ui.child.QuestionContent
import com.familyshield.app.ui.family.DraftAudio
import com.familyshield.app.ui.family.FamilyHomeContent
import com.familyshield.app.ui.family.FamilyUiState
import com.familyshield.app.ui.family.NewCaseContent
import com.familyshield.app.ui.theme.FamilyShieldTheme
import com.familyshield.app.ui.v3.HomeTab
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import java.time.Instant

@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [33], qualifiers = "ko-rKR-w390dp-h844dp")
class V3ScreenshotTest {
    @get:Rule
    val compose = createAndroidComposeRule<ComponentActivity>()

    private val now = Instant.parse("2026-11-11T12:24:00Z")
    private val deadline = "2026-11-11T12:25:08Z"

    @Test fun homeIdleLight() = shot("home-idle-light", false) { home(open = false) }
    @Test fun homeIdleDark() = shot("home-idle-dark", true) { home(open = false) }
    @Test fun homeLiveLight() = shot("home-live-light", false) { home(open = true) }
    @Test fun homeLiveDark() = shot("home-live-dark", true) { home(open = true) }
    @Test fun historyLight() = shot("history-light", false) { home(open = false, tab = HomeTab.History) }
    @Test fun historyDark() = shot("history-dark", true) { home(open = false, tab = HomeTab.History) }
    @Test fun familyLight() = shot("family-light", false) { home(open = false, tab = HomeTab.Family) }
    @Test fun familyDark() = shot("family-dark", true) { home(open = false, tab = HomeTab.Family) }
    @Test fun progressLight() = shot("progress-light", false) { progress() }
    @Test fun progressDark() = shot("progress-dark", true) { progress() }
    @Test fun resultScamLight() = shot("result-scam-light", false) { result("red", "not_sent", "scam") }
    @Test fun resultScamDark() = shot("result-scam-dark", true) { result("red", "not_sent", "scam") }
    @Test fun resultConfirmedLight() = shot("result-confirmed-light", false) { result("green", "sent", "confirmed") }
    @Test fun resultConfirmedDark() = shot("result-confirmed-dark", true) { result("green", "sent", "confirmed") }
    @Test fun childLight() = shot("child-light", false) { child() }
    @Test fun childDark() = shot("child-dark", true) { child() }
    @Test fun shareLight() = shot("share-voice-light", false) { share() }
    @Test fun shareDark() = shot("share-voice-dark", true) { share() }

    @Composable
    private fun home(open: Boolean, tab: HomeTab = HomeTab.Home) {
        val recent = listOf(
            summary("case-open", "지우", "open", "waiting_push", null, if (open) deadline else null, "300만원"),
            summary("case-min", "민준", "green", "confirmed", "sent", null, "20만원", "2026-11-10T09:10:00Z"),
        ).filter { open || it.id != "case-open" }
        FamilyHomeContent(
            familyName = "우리 가족",
            parentName = "선영",
            state = FamilyUiState(
                loading = false,
                members = listOf(
                    sampleChild(id = "p", name = "선영", status = "active").copy(role = "parent"),
                    sampleChild(id = "jiwoo", name = "지우", status = "active", confirmedAt = "2026-11-01T00:00:00Z", phoneLast4 = "4821"),
                    sampleChild(id = "minjun", name = "민준", status = "active", confirmedAt = "2026-11-01T00:00:00Z", phoneLast4 = "1956"),
                ),
                recent = if (open) recent else recent.filter { it.state != "waiting_push" },
            ),
            onRefresh = {},
            onSignOut = {},
            onAdd = {},
            onVerifyChild = {},
            onNewCase = {},
            onConfirmJoin = {},
            onRejectJoin = {},
            onConfirmPhone = {},
            onRejectPhone = {},
            onReissue = {},
            onCallOnly = {},
            onOpenRecent = {},
            now = now,
            initialTab = tab,
            ticking = false,
        )
    }

    @Composable
    private fun progress() {
        CaseContent(
            case = sampleCase(
                name = "지우",
                state = "waiting_push",
                color = "open",
                parentText = "엄마, 300만원만 보내줘",
                claims = Claims(amount = "300만원"),
            ).copy(phoneLast4 = "4821", deadlineAt = deadline, createdAt = "2026-11-11T12:24:00Z"),
            pollError = false,
            onBack = {},
            now = now,
        )
    }

    @Composable
    private fun result(color: String, result: String, state: String) {
        CaseContent(
            case = sampleCase(
                name = "지우",
                color = color,
                result = result,
                state = state,
                decidedAt = "2026-11-11T12:25:00Z",
                claims = Claims(amount = "300만원", story = "tuition is due tonight"),
            ),
            pollError = false,
            onBack = {},
            now = now,
        )
    }

    @Composable
    private fun child() {
        QuestionContent(
            calling = false,
            revealedCode = null,
            callFallback = false,
            busy = false,
            error = null,
            onYes = {},
            onNo = {},
            onNotNow = {},
            onReveal = {},
            onHideCode = {},
            askerName = "선영",
            requestAmount = "300만원",
            initialChoice = "no",
        )
    }

    @Composable
    private fun share() {
        val file = File.createTempFile("note", ".m4a")
        NewCaseContent(
            state = FamilyUiState(
                loading = false,
                caseChildId = "jiwoo",
                draftAudio = DraftAudio(file, "음성 메시지.m4a", "audio/mp4"),
                fromShare = true,
            ),
            members = listOf(
                sampleChild(id = "jiwoo", name = "지우", phoneLast4 = "4821"),
                sampleChild(id = "minjun", name = "민준", phoneLast4 = "1956"),
            ),
            onBack = {},
            onSelect = {},
            onText = {},
            onVerify = {},
            onRemoveAudio = {},
        )
    }

    private fun summary(
        id: String,
        name: String,
        color: String,
        state: String,
        result: String?,
        deadline: String?,
        amount: String?,
        decided: String? = null,
    ) = CaseSummary(
        id = id,
        childMemberId = "c",
        childDisplayName = name,
        state = state,
        result = result,
        color = color,
        requestAmount = amount,
        deadlineAt = deadline,
        createdAt = "2026-11-11T12:24:00Z",
        decidedAt = decided,
    )

    private fun shot(name: String, dark: Boolean, content: @Composable () -> Unit) {
        compose.setContent {
            FamilyShieldTheme(dark = dark) {
                Box(Modifier.requiredSize(390.dp, 844.dp).testTag("v3_shot")) { content() }
            }
        }
        compose.waitForIdle()
        val view = compose.activity.window.decorView
        val width = view.width.coerceAtLeast(1)
        val height = view.height.coerceAtLeast(1)
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        view.draw(Canvas(bitmap))
        val dir = File("build/screenshots").apply { mkdirs() }
        File(dir, "$name.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }
}
