package com.familyshield.app.ui

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.familyshield.app.call.CallerLabel
import com.familyshield.app.ui.child.ChildHomeContent
import com.familyshield.app.ui.child.ChildWaitingContent
import com.familyshield.app.ui.theme.FamilyShieldTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])
class OutboundLabelScreenTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun theChildHomeOffersTheOptionalLabel() {
        compose.setContent {
            FamilyShieldTheme {
                ChildHomeContent(
                    familyName = "Lee",
                    waiting = false,
                    decided = null,
                    notice = null,
                    error = null,
                    shareNotice = null,
                    onAnswer = {},
                    onReset = {},
                    onSignOut = {},
                    onDiscardShare = null,
                    onDismissNotice = {},
                )
            }
        }
        compose.onNodeWithTag("outbound_label").assertIsDisplayed()
        compose.onNodeWithTag("open_call_screening").assertIsDisplayed()
        compose.onNodeWithText("Optional. The check code works without this.", substring = true).assertIsDisplayed()
        compose.onNodeWithText("verified", substring = true, ignoreCase = true).assertDoesNotExist()
        compose.onNodeWithTag("open_call_screening").performClick()
    }

    @Test
    fun theWaitingScreenOffersTheSameLabel() {
        compose.setContent {
            FamilyShieldTheme {
                ChildWaitingContent(
                    familyName = "Lee",
                    last4 = "5678",
                    notice = null,
                    error = null,
                    onRefresh = {},
                    onSignOut = {},
                )
            }
        }
        compose.onNodeWithTag("open_call_screening").assertIsDisplayed()
        compose.onNodeWithText("verified", substring = true, ignoreCase = true).assertDoesNotExist()
    }

    @Test
    fun theCallerIdActivitySaysFamilyShieldAndDoesNotGradeANumber() {
        compose.setContent {
            FamilyShieldTheme {
                CallerLabel(onDismiss = {})
            }
        }
        compose.onNodeWithTag("caller_label").assertIsDisplayed()
        compose.onNodeWithText("Family Shield").assertIsDisplayed()
        compose.onNodeWithText("Family Shield is calling for your family.").assertIsDisplayed()
        compose.onNodeWithText("verified", substring = true, ignoreCase = true).assertDoesNotExist()
    }
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class OutboundLabelUnavailableTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun beforeCallScreeningExistsTheCheckCodeStillWorks() {
        compose.setContent {
            FamilyShieldTheme {
                ChildHomeContent(
                    familyName = "Lee",
                    waiting = false,
                    decided = null,
                    notice = null,
                    error = null,
                    shareNotice = null,
                    onAnswer = {},
                    onReset = {},
                    onSignOut = {},
                    onDiscardShare = null,
                    onDismissNotice = {},
                )
            }
        }
        compose.onNodeWithText("This phone doesn't offer call screening. The check code still works.").assertIsDisplayed()
        compose.onNodeWithTag("open_call_screening").assertDoesNotExist()
    }
}
