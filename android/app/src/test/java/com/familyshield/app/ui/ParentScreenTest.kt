package com.familyshield.app.ui

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import com.familyshield.app.sampleCase
import com.familyshield.app.sampleChild
import com.familyshield.app.ui.caseflow.CaseContent
import com.familyshield.app.ui.family.FamilyHomeContent
import com.familyshield.app.ui.family.FamilyUiState
import com.familyshield.app.ui.theme.FamilyShieldTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])
class ParentScreenTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun emptyFamily() {
        compose.setContent {
            FamilyShieldTheme {
                FamilyHomeContent(
                    familyName = "Lee",
                    state = FamilyUiState(loading = false),
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
                )
            }
        }
        compose.onNodeWithText("No children yet").assertIsDisplayed()
    }

    @Test
    fun unconfirmedChildDisablesVerify() {
        val pending = sampleChild(
            awaitingConfirm = true,
            linked = true,
            phoneVerified = true,
            phoneLast4 = "0123",
            confirmedAt = null,
            status = "invited",
        )
        compose.setContent {
            FamilyShieldTheme {
                FamilyHomeContent(
                    familyName = "Lee",
                    state = FamilyUiState(loading = false, members = listOf(pending)),
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
                )
            }
        }
        compose.onNodeWithText("Can't verify yet: confirm Mina first.").assertIsDisplayed()
        compose.onNodeWithTag("verify_child-1").assertIsNotEnabled()
    }

    @Test
    fun yellowResult() {
        compose.setContent {
            FamilyShieldTheme {
                CaseContent(
                    case = sampleCase(
                        color = "yellow",
                        result = "wrong",
                        state = "not_confirmed",
                        decidedAt = "2026-11-07T15:04:00+00:00",
                    ),
                    pollError = false,
                    onBack = {},
                )
            }
        }
        compose.onNodeWithText("Not confirmed").assertIsDisplayed()
        compose.onNodeWithText("Don't send money", substring = true).assertIsDisplayed()
        compose.onNodeWithText("was wrong", substring = true).assertIsDisplayed()
    }

    @Test
    fun redResultOffersTheFamilyWarning() {
        compose.setContent {
            FamilyShieldTheme {
                CaseContent(
                    case = sampleCase(
                        color = "red",
                        result = "not_sent",
                        state = "scam",
                        decidedAt = "2026-11-07T15:04:00+00:00",
                    ),
                    pollError = false,
                    onBack = {},
                )
            }
        }
        compose.onNodeWithText("Scam").assertIsDisplayed()
        compose.onNodeWithText("Do not send money", substring = true).assertIsDisplayed()
        compose.onNodeWithText("Warn your family").assertIsDisplayed()
    }
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33], qualifiers = "ko")
class KoreanResultTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun redResultInKorean() {
        compose.setContent {
            FamilyShieldTheme {
                CaseContent(
                    case = sampleCase(
                        color = "red",
                        result = "not_sent",
                        state = "scam",
                        name = "민지",
                        decidedAt = "2026-11-07T15:04:00+00:00",
                    ),
                    pollError = false,
                    onBack = {},
                )
            }
        }
        compose.onNodeWithText("돈을 보내지 마세요", substring = true).assertIsDisplayed()
        compose.onNodeWithText("가족에게 알리세요").assertIsDisplayed()
    }
}
